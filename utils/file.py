import base64
import os
import urllib.request
from datetime import datetime


def get_current_dir():
    return os.getcwd()


def get_file_size(file_path):
    with open(file_path, "rb") as f:
        file_size = os.fstat(f.fileno()).st_size

    return file_size


def delete_file(file_path):
    os.remove(file_path)


def download_image(imgURL: str, name: str or int = "Image", extension: str = "jpg") -> str or None:
    print(f"Downloading {imgURL}")
    path = f"downloads/{datetime.today().strftime('%Y-%m-%d')}"
    is_exist = os.path.exists(path)
    if not is_exist:
        os.makedirs(path)

    full_path = os.path.abspath(os.getcwd() + f"/{path}/{name}-{datetime.utcnow().timestamp()}.{extension}")
    try:
        urllib.request.urlretrieve(imgURL, full_path)

        if get_file_size(full_path) <= 10000:
            delete_file(full_path)
            return None

        print(f"Downloaded {imgURL} to {full_path}")
        return full_path
    except Exception as e:
        print(f"Something wrong! {e} : URL {imgURL}")
        return None


def base64_to_image_file(base64_string: str, name: str or int = "Image", extension: str = "jpg"):
    path = f"media/image/{datetime.today().strftime('%Y-%m-%d')}-base64"
    is_exist = os.path.exists(path)
    if not is_exist:
        os.makedirs(path)

    full_path = os.path.abspath(os.getcwd() + f"/{path}/{name}-{datetime.utcnow().timestamp()}.{extension}")
    try:
        # Decode the base64 string into bytes
        image_data = base64.b64decode(base64_string)

        # Write the bytes to an image file
        with open(full_path, "wb") as image_file:
            image_file.write(image_data)

        print(f"Image saved to {full_path}")
        return full_path
    except Exception as e:
        print("Error:", str(e))
        return None


def file_dir_to_download_url(file_dir: str):
    base_url = os.getenv('BASE_URL')

    # Split the path based on the "downloads" directory
    parts = file_dir.split('/downloads/')

    # Check if the path contains the "downloads" directory
    if len(parts) > 1:
        # Get the portion of the path after "downloads/"
        sub_path = parts[1]

        # Construct the URL by appending sub_path to the base URL
        url = f'{base_url}/downloads/{sub_path}'

        return url

    return f"Incorrect path: {file_dir}"


def is_image_file(filename):
    image_extensions = ['.jpg', '.jpeg', '.png', '.gif']
    return any(filename.lower().endswith(ext) for ext in image_extensions)
