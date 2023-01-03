const copyToClipboard = (el) => {
    console.log(el.value);
    window.navigator.clipboard.writeText(el.value).then(res => {
        alert("복사되었습니다.");
    });
}

const openPopup = (url, name) => {
    const option = "width = 500, height = 500, top = 100, left = 200, location = no"
    window.open(url, name,)
}