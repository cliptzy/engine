import os
import json
import requests
from core.config import config
from core.logger import log as logger

def check_youtube_auth() -> tuple[bool, str]:
    token_file = "youtube_token.json"
    if not os.path.exists(token_file):
        return False, "Token file tidak ditemukan. Silakan lakukan upload sekali untuk memicu login browser."
        
    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        
        with open(token_file, "r", encoding="utf-8") as f:
            creds_data = json.load(f)
            
        creds = Credentials.from_authorized_user_info(creds_data)
        if not creds.valid:
            if creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    with open(token_file, 'w', encoding="utf-8") as f:
                        f.write(creds.to_json())
                    return True, "Token berhasil diperbarui (direfresh) dan aktif."
                except Exception as e:
                    return False, f"Gagal refresh token: {str(e)}"
            else:
                return False, "Token kadaluarsa dan tidak bisa direfresh."
        return True, "Token valid dan aktif."
    except Exception as e:
        logger.error(f"Error check_youtube_auth: {e}")
        return False, f"Error validasi token: {str(e)}"

def check_tiktok_auth() -> tuple[bool, str]:
    if not config.tt_session:
        return False, "Session ID belum diisi."
        
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        cookies = {
            "sessionid": config.tt_session
        }
        
        if len(config.tt_session) < 20:
            return False, "Session ID sepertinya tidak valid (terlalu pendek)."
            
        resp = requests.get("https://www.tiktok.com/passport/web/account/info/", cookies=cookies, headers=headers, timeout=15)
        
        if resp.status_code == 200:
            data = resp.json()
            if data.get("data", {}).get("user_id") or data.get("message") == "success":
                return True, "Session ID TikTok valid dan aktif."
            else:
                return False, "Session ID tidak valid atau sudah expired."
        
        return False, f"Gagal mengecek session (HTTP {resp.status_code})."
    except Exception as e:
        logger.error(f"Error check_tiktok_auth: {e}")
        return False, f"Gagal menghubungi server TikTok: {str(e)}"

def check_instagram_auth() -> tuple[bool, str]:
    if not config.ig_access_token or not config.ig_business_id:
        return False, "Access Token atau Business ID belum diisi."
        
    try:
        url = f"https://graph.facebook.com/v18.0/{config.ig_business_id}?access_token={config.ig_access_token}"
        resp = requests.get(url, timeout=15)
        data = resp.json()
        
        if "id" in data:
            return True, f"Instagram Graph API terhubung dengan baik. ID: {data['id']}"
        elif "error" in data:
            err_msg = data["error"].get("message", "Unknown error")
            return False, f"Token tidak valid: {err_msg}"
            
        return False, "Respons API tidak dikenali."
    except Exception as e:
        logger.error(f"Error check_instagram_auth: {e}")
        return False, f"Gagal menghubungi Graph API: {str(e)}"
