from rest_framework.response import Response

class Success(Response):
    def __init__(self, data=None, message="Success", status=200):
        payload = {
            "success": True,
            "message": message,
            "data": data,
        }
        super().__init__(payload, status=status)


class Error(Response):
    def __init__(self, code=400, message="Error", data=None):
        payload = {
            "success": False,
            "code": code,
            "message": message,
            "data": data,
        }
        super().__init__(payload, status=400)
