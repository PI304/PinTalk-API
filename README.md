# PinTalk Chat

핀톡 내 채팅 피처와 관련한 스펙을 정리하는 곳

## Contents
1. [Managing Chat Message Data](#1-managing-chat-message-data)
2. [Websocket Connections](#2-websocket-connections)
3. [Closing Chatrooms](#3-closing-chatrooms)
4. [Checking Online Status](#4-checking-online-status)
5. [Error Codes](#5-error-codes)
6. [Checking New Messages](#6-checking-new-messages)
7. [Top-Fixing Chatrooms](#7-top-fixing-chatrooms)



## 1. Managing Chat Message Data
> PinTalk 은 데이터를 저장하는 공간으로 Redis 와 MySQL 을 사용합니다. 
> 채팅 메시지들은 보내지는 즉시 Redis 에 저장되고, 이와 동시에 비동기적으로 MySQL 에도 저장됩니다.

위와 같은 방침을 선택한 이유는 핀톡 서비스가 많은 채팅량이나 대규모 트래픽을 기대하지 않기 때문입니다.
일정 기간 동안 Redis 에 메시지 데이터를 모았뒀다가 주기적으로 MySQL 에 dump 하는 방법이나,
Realtime Database (ex. DynamoDB, Firebase Realtime) 을 사용하여 바로 데이터베이스에 추가하는 방법도 고려해보았으나,
서비스의 특성이나 규모에 맞지 않는다고 판단하여 위와 같은 방법으로 데이터를 보존하게 되었습니다.

PinTalk 서비스에서는 유저 정보를 제외한, 채팅과 관련된 사용자의 데이터를 주기적으로
삭제합니다. 
아래는 사용자 데이터가 삭제되는 케이스들 입니다.

1. 채팅 종료 시 (```is_closed```), Redis 에 있는 메시지 데이터는 삭제됩니다.
2. 채팅 종료 후 (```is_closed```) 아무런 활동 없이, 즉 재개(resume) 없이 7일이 지나면, MySQL 에 저장된 메시지 데이터가 삭제됩니다. (이때, 1번에 의해 Redis 내 데이터는 이미 삭제된 상태입니다.)
3. 관리자 페이지에서 '채팅 나가기' 를 수행하면,  MySQL 에 남아 있는 모든 채팅 메시지가 즉시 삭제됩니다. *채팅방 나가기를 수행하기 위해선 우선 채팅 종료하기 를 수행해야 합니다.*
4. 채팅이 재개되지 않은 채로 1주일이 지나면, 채팅방은 자동으로 **종료 처리**가 됩니다.

### 채팅을 종료하는 방법
채팅의 종료는 웹소켓 연결을 통해 수행합니다. 채팅을 종료하려면 다음과 같은 메시지를 웹소켓을 통해 전송하도록 합니다.
```json
{
   "type": "notice",
   "message": "closed",
   "datetime": "2023-03-25T14:32:57.123",
   "is_host": true
}
```

사용자가 위와 같은 메시지를 보냈을 때 게스트가 웹소켓에 연결되어 있다면 이를 통해 해당 메시지가 수신되고, 
그 즉시 웹소켓 연결은 자동으로 끊기게 됩니다.


## 2. Websocket Connections
아래는 FE 에서 웹소켓을 연결하여 채팅방에 접속하는 방법에 관한 세부사항입니다.


### 1) 채팅방 생성하기 - NPM Package 의 경우
> ⚠️ 채팅방을 생성할 수 있는 주체는 Guest 입니다. 관리자 페이지에서는 채팅방을 생성할 수 없습니다.


```/api/chat/``` 엔드포인트로 POST 요청을 보냅니다. 이때 body 는 비어있는 상태로 보내며, 아래와 같이 커스텀 헤더를 추가하도록 합니다.
```text
X-PinTalk-Access-Key: d20aF0TvSdeWk-iPXf3l_Q
X-PinTalk-Secret-Key: 669da7488fe5c7baee216ba0f8f9b8e7f93113b40b0e8d658d60b05a090bc0dd
```

> Access Key 와 Secret Key 를 비롯한 유저 정보는 ```/api/users/client``` 엔드포인트에서 받을 수 있습니다. 
> 이 경우 역시, 커스텀 헤더를 위와 같이 추가하여 GET 요청을 보내도록 합니다.

```/api/chat/``` 엔드포인트로 POST 요청을 보내면, 아래와 같은 응답을 받게 됩니다.
```json
{
  "host": {
    "email": "user@example.com",
     "uuid": "NsNVwaNrkUbrgnkGfsTuuA",
    "profileName": "string",
    "description": "string",
    "serviceName": "string",
    "profileImage": "string"
  },
  "guest": "string",
  "name": "string",
  "isClosed": true,
  "closedAt": "2023-03-21T02:05:23.443Z",
  "createdAt": "2023-03-21T02:05:23.443Z",
  "updatedAt": "2023-03-21T02:05:23.443Z"
}
```
위 json 데이터에서 ```name``` 필드는 채팅방에 부여되는 고유한 이름입니다. 채팅방에 입장을 할 때 이 이름을 사용하게 됩니다.

**채팅방 재입장을 구현할 때에는 이 ```name``` 필드의 값을 저장해두도록 합니다.**

### 2) 웹소켓 연결하기

패키지에서는 1) 번과 같이 채팅방 이름을 습득할 수 있는 반면, 관리자 페이지에서는 로그인한 유저의 
채팅방 목록을 GET 해오는 방식으로 채팅방 이름에 대한 정보를 습득할 수 있습니다. 

관리자 페이지에서는 ```/api/chat/chatrooms/``` 엔드포인트에 GET 요청을 보냄으로써 요청을 보내는 유저의
모든 채팅방 목록을 받아볼 수 있습니다. 요청에 대한 응답은 아래 json 과 같습니다.

```json
{
  "count": 0,
  "next": "string",
  "previous": "string",
  "results": [
    {
      "id": 0, 
      "host": 0,
      "guest": "string",
      "name": "string",
      "latestMsg": "string", 
      "latestMsgAt": "2023-03-21T03:58:57.178Z", 
      "lastCheckedAt": "2023-03-21T03:58:57.178Z",
      "isClosed": true,
      "closedAt": "2023-03-21T03:58:57.178Z",
      "isFixed": true,
      "fixedAt": "2023-03-21T03:58:57.178Z",
      "createdAt": "2023-03-21T03:58:57.178Z",
      "updatedAt": "2023-03-21T03:58:57.178Z"
    }
  ]
}
```

위 json 데이터의 ```name``` 필드가 채팅방의 고유 이름을 가리킵니다.

채팅방 이름을 습득하였다면, 이제 웹소켓에 연결해야 합니다.

**PinTalk 채팅 서버를 이용하기 위해서는 [WebSocket API](https://developer.mozilla.org/en-US/docs/Web/API/WebSockets_API) 를 직접적으로 사용해야 합니다. 
Socket.io 와 같은 패키지는 사용할 수 없습니다. 아래는 socket.io README 에서 발췌한 내용입니다.**

> Note: Socket.IO is **not a WebSocket implementation.** Although Socket.IO indeed uses WebSocket as a transport when possible, it adds some metadata to each packet: the packet type, the namespace and the ack id when a message acknowledgement is needed. That is why a WebSocket client will not be able to successfully connect to a Socket.IO server, and a Socket.IO client will not be able to connect to a WebSocket server (like ws://echo.websocket.org) either. Please see the protocol specification here.

채팅방 이름을 path 에 명시하여 웹소켓 연결을 진행합니다. 아래 코드는 javascript 의 WebSocket API 를 사용하여 
채팅방에 입장하는 예제 코드입니다. 

```javascript
const request_uri = `ws://3.34.7.189/ws/chat/${roomName}/`;
chatSocket = new WebSocket(request_uri);
chatSocket.onopen = () => {
    console.log('connected');
}
```

위 코드를 통해 생성한 WebSocket 인스턴스에 이벤트 리스너 (ex. onopen, onmessage, onclose 등) 를 등록하여 다양한 케이스를 처리합니다.


### 3) Authentication for Websocket Connections 

websocket 에 성공적으로 연결되기 위해선 credential 확인이 필요합니다.
익명의 게스트가 채팅방에 입장하는 패키지의 방식과 JWT 인증 플로우를 사용하는 관리자
페이지의 방식으로 나뉨에 따라, 각각 그 과정이 다릅니다.

1. 익명의 게스트가 입장하는 경우
   - websocket 연결을 요청하면 그 헤더로 Origin 에 대한 정보가 함께 전송됩니다.
   - 서버에서는 이 헤더를 검사하여 핀톡 사용자 (개발자) 가 ```service_domain``` 에 등록해둔 도메인과 일치한다면 요청을 허용합니다.

2. 이미 인증 과정을 거쳐 관리자 페이지에 로그인한 유저가 입장하는 경우
    - websocket 연결을 요청하는 uri 에 쿼리 스트링으로 access token 을 추가합니다.
    - [2. WebSocket Connections](#2-websocket-connections) 섹션의 예제 코드로 제시했던 uri 뒤에 ```token``` 이라는 이름으로 쿼리 스트링을 추가해야합니다.
    - ```const request_uri = `ws://3.34.7.189/ws/chat/${roomName}/?token=${user'stoken}`;```
         > ⚠️ jwt token 은 delimiter 로 온점(.) 을 사용합니다. 하지만, query string 에 온점을 포함시키면 separator 로 인식하는 경우가 있으므로 
         > manual 하게 온점을 슬래쉬(/) 로 바꾸어 전달하도록 합니다.
    - 이 토큰을 사용하여 authenticate 과정을 거친 후 웹소켓 연결을 승인합니다.

### 4) Chat Message Data
메시지를 주고 받을 때에는 합의된 형태가 있어야 합니다. 기본적인 형태는 아래와 같습니다.

```javascript
// datetime format
const getDatetime = () => {
   const now = new Date();
   now.setHours(now.getHours() + 9);
   const dateStr = now.toISOString().substring(0, 23);

   return dateStr;
}

// 메시지를 보낼 때
chatSocket.send(JSON.stringify({
     type: 'chat_message',
     is_host: false,
     message: message,
     datetime: getDatetime()
 }));

// 메시지를 받을 때
chatSocket.onmessage = function(e) {
    const data = JSON.parse(e.data);
    console.log(data);
    // Do something here
};
```
- ```type```: 메시지의 종류를 명시합니다. 
  - ```chat_message```: 게스트와 사용자가 주고받는 일반적인 채팅 메시지
  - ```notice```: 상태 확인 등 알림의 성질을 띠는 메시지
  - ```request```: 서버에 특정 자원을 요청하는 메시지
- ```is_host```: 메시지를 작성한 주체를 명시합니다. ```true``` 일 경우, 사용자가 작성한 메시지이며, ```false``` 인 경우 게스트가 작성한 메시지입니다.
  - ```datetime```: 메시지를 보낸 시각이 ```%T-%m-%dT-%H:%M:%S.%f``` 형태로 담겨 있습니다.
  >   메시지를 보낸 시각은 다른 메시지의 전송 시각과 최대한 겹치지 않게 하기 위해서 밀리세컨드까지의 정보를 포함하도록 합니다. 위 ```getDatetime``` 함수를 이용하면 소수점 세자리까지의 밀리세컨드 정보를 담을 수 있습니다.
- ```message```: 실제 메시지의 내용입니다.

> ```notice``` 타입의 메시지는 online status 확인용 웹소켓에서 주로 쓰입니다. [4. Checking Online Status](#4-checking-online-status) 섹션을 확인하세요.

채팅용 웹소켓에 연결했을 때 서버는 해당 소켓으로 최근순으로 50 개의 메시지를 소켓으로 보냅니다. 
(과거에 주고받은 채팅 메시지가 50개를 넘지 않는 경우 50개보다 적은 개수의 메시지가 보내집니다.)
50개의 메시지보다 더 과거의 데이터가 필요하다면 서버에 새로운 요청을 보내야 합니다. 
이 요청은 웹소켓 안에서 이루어지며 전송하는 메시지의 타입을 ```request``` 로 지정해야 합니다.
구체적인 요청 메시지 형태는 아래와 같습니다.

```json
{
  "type": "request",
  "is_host": true,
  "message": "2023-03-15T20:13:77.123",
  "datetime": "2023-03-23T08:15:77.123"
}
```
```datetime``` 필드는 채팅 메시지와 동일하게 해당 요청을 보내는 시간을 담는 것이며 ```message``` 필드에는
어느 시점부터의 메시지를 불러오고 싶은지 명시합니다. 서버는 처음 소켓에 연결되었을 때와 동일하게, ```message``` 필드에
명시된 시점에서 최신순으로 50개의 메시지를 보냅니다.

> ⚠️ 과거의 메시지를 한번에 받아올 때와 하나의 메시지만을 수신할 때의 데이터 형태는 다릅니다. 아래를 참고해주세요.

메시지 한 개를 받는 상황
```json
{
  "type": "chat_message",
  "is_host": true,
  "message": "hi",
  "datetime": "2023-03-23T08:15:77.123"
}
```

과거 메시지를 여러 개 받는 상황 (처음에 소켓 접속 시, request 타입으로 과거 메시지 요청 시)
```json 
{
  "data": [
    { "type": "chat_message", "is_host": true, "message": "hi", "datetime": "2023-03-23T08:15:77.123"},
    { "type": "chat_message", "is_host": true, "message": "hi", "datetime": "2023-03-23T08:15:77.123"},
    { "type": "chat_message", "is_host": true, "message": "hi", "datetime": "2023-03-23T08:15:77.123"},
  ],
  "type": "chat_message"
}
```

## 3. Closing Chatrooms
사용자는 게스트와의 대화를 종료할 수 있습니다. *채팅 종료* 는 *채팅방 나가기* 와는 다른 기능이며 그 차이는
[1. Managing Chat Message Data](#1-managing-chat-message-data) 섹션을 확인해주세요.

채팅을 종료하기 위한 요청은 소켓을 통해 이루어지며, 메시지 타입은 ```notice``` 입니다.
아래는 서버에 채팅 종료를 요청하는 예시입니다.

```javascript
chatSocket.send(JSON.stringify({
     type: 'notice',
     is_host: true,
     message: "close",
     datetime: getDatetime()
 }));
```
해당 요청을 보내면 chatroom 데이터의 ```is_closed``` 필드가 ```True``` 로 저장되고.
채팅이 종료 처리가 되었다는 메시지를 수신 받은 뒤, 자동으로 소켓의 연결이 끊기게 됩니다.
아래는 채팅 종료 처리 시, 사용자와 게스트가 받게 될 메시지입니다.
```json
{
  "type": "notice",
  "is_host": true,
  "message": "closed",
  "datetime": "2023-03-23T08:15:77.123"
}
```
> ⚠️ 종료된 채팅방에 소켓 연결을 시도하면, 4009 소켓 에러가 반환됩니다.

## 4. Checking Online Status
채팅방에 입장한 게스트는 사용자 (개발자) 가 현재 관리자 페이지에 접속해있는지의 여부를 확인할 수 있습니다.
사용자는 본인의 상태가 변화할 때마다 소켓에 본인의 상태에 대한 메시지를 전송히고 게스트는 사용자가 보낸 가장 최근의
메시지를 보고 사용자의 상태를 파악합니다.

#### 사용자의 경우
1. 사용자가 로그인할 때, 관리자 페이지에서 새로운 (상태확인용) 웹소켓을 연결하고 연결을 유지합니다.
2. 사용자가 로그아웃을 하거나 브라우저 탭을 끈 경우, 해당 웹소켓에서 연결을 해제합니다.

#### 게스트의 경우
1. 게스트가 채팅방에 입장할 때, 채팅방 관련 웹소켓이 아닌 사용자의 온라인 여부를 파악할 수 있는 새로운 (상태확인용) 웹소켓을 연결합니다.
2. 연결을 하면 사용자의 최근 상태에 대한 메시지가 전송됩니다. 해당 메시지의 ```message``` 필드를 보고 현재 사용자가 offline 인지 online 인지 파악할 수 있습니다.
3. 중간에 사용자가 접속을 하거나 접속을 끊을 수 있기 때문에 웹소켓과의 연결을 유지하며 새로운 상태 메시지가 수신되는지 onmessage 이벤트를 통해 확인합니다.

> ⚠️ 이때의 소켓은 대화용 소켓이 아닌 **온라인/오프라인 여부 확인을 위해 쓰이는 소켓**입니다. 즉, 결과적으로는 대화용 소켓과 상태확인용 소켓, 2 종류의 소켓에 연결해야합니다.

상태를 알리는 메시지의 형태는 아래와 같습니다.
```json
{
  "type": "notice",
  "is_host": false,
  "message": "online",
  "datetime": "2023-03-23T08:15:77.123"
}
```

---

status 확인용 websocket 에 연결하는 방법은 다음과 같습니다. 

사용자 (관리자 페이지 쪽) 는 아래 uri 에 이전에 소개했던 것처럼 ```?token=sometoken``` 과 같이 쿼리 스트링을 추가해주어야 합니다.

> ⚠️ jwt token 은 delimiter 로 온점(.) 을 사용합니다. 하지만, query string 에 온점을 포함시키면 separator 로 인식하는 경우가 있으므로 
> manual 하게 온점을 슬래쉬(/) 로 바꾸어 전달하도록 합니다.

```javascript
const request_uri = `ws://3.34.7.189/ws/status/${hostUuid}/`;
chatSocket = new WebSocket(request_uri);
chatSocket.onopen = () => {
    console.log('connected');
}
```

**PinTalk 패키지 개발 시, 해당 웹소켓에 연결하여 전송받는 메시지들을 모니터링하고, 그 내용에 따라 status 를 반영해주어야 합니다.**


## 5. Error Codes
웹소켓의 close event 에는 HTTP 프로토콜처럼 code 가 포함되어 있습니다. 보편적인 close event 의 code는 [여기 링크](https://developer.mozilla.org/en-US/docs/Web/API/CloseEvent/code) 에서 확인해볼 수 있습니다.

4000번부터는 custom error code 입니다. PinTalk 에서는 다음과 같은 커스텀 코드를 이용합니다.

### Chat Socket 의 경우
- **4000**: HTTP 의 Bad Request(400) 와 유사, 메시지의 형태가 약속에 어긋남
- **4003**: HTTP 의 Permission Denied(403) 와 유사, 게스트의 Origin 이 허용되지 않은 도메인임
- **4004**: HTTP 의 Not Found(404) 와 유사, 요청 uri 의 채팅방 이름이 존재하지 않음
- **4009**: HTTP 의 Conflict(409) 와 유사, 종료된 채팅방임. 재개하기 후 재연결 시도해야함 (단, 게스트 사이드의 경우 서버에서 재개를 한 뒤, 종료되어 있었던 채팅방임을 알리기 위해서 4009 에러 반환)


### Status Socket 의 경우
- **4003**: HTTP 의 Permission Denied(403) 와 유사, 게스트의 Origin 이 허용되지 않은 도메인임
- **4004**: HTTP 의 Not Found(404) 와 유사, 요청 uri 의 uuid 를 가진 유저가 존재하지 않거나 올바르지 않음
- **4009**: HTTP 의 Conflict(409) 와 유사, online status 사용을 활성화 해두지 않은 유저임


## 6. Checking New Messages
관리자 페이지에서 사용자는 읽지 않은 새로운 메시지가 있는 채팅방을 구분할 수 있어야 합니다. 또한 새로운 메시지의
내용 역시 채팅방 목록에서 미리 볼 수 있어야 합니다. 이를 위해 chatroom 데이터는 아래와 같은 필드들을 가지고 있습니다.
전체 데이터는 섹션 [2. Websocket Connections](#2-websocket-connections) 에서 다시 확인해볼 수 있습니다.

* ```lastestMsg```: 가장 최근에 보낸 메시지의 내용
* ```latestMsgAt```: 가장 최근에 보낸 메시지의 시간
* ```lastCheckedAt```: 사용자가 마지막으로 채팅방을 확인한 시간


```latestMsgAt``` 의 시간이 ```lastCheckedAt``` 의 시간보다 더 최근의 시간일 경우,
사용자가 확인하지 않은 새로운 메시지가 도착했다는 것을 의미합니다.


## 7. Top-Fixing Chatrooms
유저는 **총 5개**까지의 채팅방을 상단 고정할 수 있습니다. 상단 고정을 하는 기능은 백엔드 서버를 통해서 
수행하는 것이 아닌, **프론트엔드에서 로컬 스토리지나 쿠키를 이용해서 구현**하도록 합니다.

<!-- Security scan triggered at 2025-09-01 22:49:12 -->

<!-- Security scan triggered at 2025-09-07 01:44:39 -->