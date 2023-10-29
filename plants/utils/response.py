from django.http import JsonResponse

def make_response(data=None, message: str = "", status_code=200, error_data=None):
    status = True if (200 <= status_code < 400) else False
    data = {
        "data": data,
        "status": status,
        "message": message
    }
    if error_data:
        data['error_data'] = error_data
    elif (error_data is None) and (not status) and (len(message)>0):
        data['error_data'] = message


    return JsonResponse(data, status=status_code)