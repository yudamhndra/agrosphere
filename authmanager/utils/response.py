from django.http import JsonResponse


def make_response(data=None, message: str = "", status_code=200, error_data=None):
    status = True if (200 <= status_code < 400) else False
    data = {
        "data": data,
        "status": status,
        "message": message
    }
    if error_data: data['error_data'] = error_data

    return JsonResponse(data, status=status_code)
