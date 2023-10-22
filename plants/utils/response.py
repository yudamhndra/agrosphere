from django.http import JsonResponse


def make_response(data, message : str, res_status_code=200):
    paginate = None

    try:
        if data.get("paginate") and data.get("results"):
            paginate = data["paginate"]
            data.pop("paginate")
            data = data.get("results", [])
    except:
        pass

    status = True if (200 <= res_status_code < 400) else False
    data = {
        "data": data,
        "status": status,
        "message" : message
    }
    if paginate: data['paginate'] = paginate

    return JsonResponse(data, status=res_status_code)
