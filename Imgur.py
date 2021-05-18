import requests, json

_clientID=""

def loadUser(clientID):
    global _clientID
    _clientID = clientID


class ImageData:
    def __init__(self, data):
        for _ in data:
            setattr(self, _, data[_])

def upload(img, name="", album="", description="", filetype="file"):
    if _clientID == '':
        print('[Imgur Error] Invalid clientID:', _clientID)
    
    # type = file/url/bin
    if filetype=="file":
        print("Uploading file:", img)
        try:
            with open(img, "rb") as f:
                img = f.read()
        except:
            # cannot read file or file not exists
            return #None
    response = requests.post("https://api.imgur.com/3/upload",
                        data={"image":img,
                              "name" :name,
                              "album":album,
                              "type" :"url" if filetype=="url" else "file",
                              "description":description},
                        headers={"Authorization":f"Client-ID {_clientID}"})
    #print(response.text)
    result = response.json()
    #print(result)
    if result:
        if "errors" in result:
            error = result["errors"][0]
            if error["code"]==429:
                print(f"[{error['code']}] {error['status']}")
                print(response.headers)
            else:
                print(f"[{error['code']}] {error['status']}")
        elif result["code"]==200 and "data" in result:
            return ImageData(result["data"])
        else:
            print("Uncaught error in Imgur.py")
    else:
        print("[Imgur Error] No Response...")
        # upload failed, invalid clientID, img, albumID or file
        return #None
