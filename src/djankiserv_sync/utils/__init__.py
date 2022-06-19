from django.conf import settings


def print_request(request):
    try:
        if settings.DEBUG:
            print(pretty_request(request))
    except NameError:
        pass  # we haven't defined it, so can't be interested


def pretty_request(request):
    headers = ""
    for header, value in request.META.items():
        if not header.startswith("HTTP"):
            continue
        # header = "-".join([h.capitalize() for h in header[5:].lower().split("_")])
        header = "-".join([h.capitalize() for h in header.lower().split("_")])
        headers += "{}: {}\n".format(header, value)

    return (
        "{path}\n"
        "{method} HTTP/1.1\n"
        "Content-Length: {content_length}\n"
        "Content-Type: {content_type}\n"
        "{headers}\n\n"
        "{body}\n\n"
    ).format(
        path=request.path,
        method=request.method,
        content_length=request.META.get("CONTENT_LENGTH"),
        content_type=request.META.get("CONTENT_TYPE"),
        headers=headers,
        body=request.data,
    )
