from rest_framework.renderers import JSONRenderer


class CustomRenderer(JSONRenderer):
    def render(self, data, accepted_media_type=None, renderer_context=None):
        status_code = renderer_context["response"].status_code
        response = {}

        if not str(status_code).startswith("2"):
            # 에러 일 때
            response["code"] = status_code
            response["detail"] = data["detail"]
        else:
            response = data

        return super(CustomRenderer, self).render(
            response, accepted_media_type, renderer_context
        )
