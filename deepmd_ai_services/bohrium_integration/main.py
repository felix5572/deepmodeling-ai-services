import gradio as gr
from bohrium_open_sdk import OpenSDK
from http.cookies import SimpleCookie
import os
from jose import jwt
from datetime import datetime, timedelta, timezone

TARGET_URL = os.getenv("TARGET_URL", "https://deepmodeling-ai.deepmd.us/api/users/jwt/bohrium-proxy/callback")
BOHRIUM_PROXY_JWT_PRIVATE_KEY = os.getenv("BOHRIUM_PROXY_JWT_PRIVATE_KEY")

def instant_redirect(request: gr.Request):
    """get cookie and redirect"""
    try:
        cookie_header = request.headers.get("cookie")
        simple_cookie = SimpleCookie()
        simple_cookie.load(cookie_header)

        access_key = simple_cookie["appAccessKey"].value
        app_key = simple_cookie["clientName"].value


        client = OpenSDK(access_key=access_key, app_key=app_key)
        user_info = client.user.get_info()
        user_data = user_info['data']

        now = datetime.now(timezone.utc)
        payload = {"user_data": user_data, "iat": now, "exp": now + timedelta(minutes=30)}
        auth_token = jwt.encode(payload, BOHRIUM_PROXY_JWT_PRIVATE_KEY, algorithm="RS256")

        # separator = "&" if "?" in TARGET_URL else "?"
        # redirect_url = f"{TARGET_URL}{separator}external_jwt={auth_token}"
        
        html = f"""
            <form id="autoForm" method="POST" action="{TARGET_URL}" target="_top" style="display:none;">
                <input type="hidden" name="external_jwt" value="{auth_token}">
            </form>
            <script>
            console.log("window.onload event triggered. form/link action initiated.");
            </script>
            <p>🚀 starting to your personal page and service: {TARGET_URL} ...</p>
            <p>🖱️ If not automatically started, please <a href="#" onclick="document.getElementById('autoForm').submit(); return false;">click here</a></p>
            """
        return html
    except Exception as e:
        return f"error: {str(e)}"


with gr.Blocks(title="Redirecting...") as demo:
    output = gr.HTML()
    trigger_btn = gr.Button("Submit", visible=True) 

    demo.load(
        fn=instant_redirect, 
        outputs=output
    )

    trigger_btn.click(
        fn=lambda: None,
        _js="""
        () => {
            document.getElementById('autoForm').submit();
        }
        """
    )
    

if __name__ == "__main__":
    demo.launch(server_name='0.0.0.0', server_port=8080, show_api=False)