#!/usr/bin/env python3
"""
i18n.py - Minimal translation layer for 5AI
============================================
A tiny, dependency-free translation helper. Call set_language("en" | "tr")
to switch the active language, and t("key") anywhere in the UI to fetch the
translated string for the current language.
"""

TRANSLATIONS = {
    "en": {
        "app_name": "5AI",
        "sign_in_title": "5AI — Sign in",
        "welcome_back": "Welcome back — sign in to continue",
        "username": "Username",
        "password": "Password",
        "remember_me": "Remember me",
        "log_in": "Log In",
        "no_account": "Don't have an account? Register",
        "choose_username": "Choose a username",
        "choose_password": "Choose a password",
        "confirm_password": "Confirm password",
        "create_account": "Create Account",
        "have_account": "Already have an account? Log in",
        "enter_both": "Please enter both username and password.",
        "fill_all_fields": "Please fill out all fields.",
        "passwords_no_match": "Passwords do not match.",
        "invalid_credentials": "Invalid username or password.",
        "new_chat": "New Chat",
        "new_chat_default_title": "New chat",
        "settings": "Settings",
        "log_out": "Log out",
        "delete_chat_tooltip": "Delete this chat",
        "delete_chat_title": "Delete chat",
        "delete_chat_confirm": "Delete this conversation? This cannot be undone.",
        "typing": "5AI is typing…",
        "message_placeholder": "Message 5AI…",
        "header_assistant": "5AI Assistant",
        "account_section": "ACCOUNT",
        "signed_in_as": "Signed in as",
        "model_section": "AI MODEL",
        "model_label": "Model",
        "language_section": "LANGUAGE",
        "language_label": "App language",
        "english": "English",
        "turkish": "Türkçe",
        "actions_section": "ACTIONS",
        "clear_conversation": "Clear current conversation",
        "close": "Close",
        "account_created": "Account created successfully.",
        "username_exists": "Username already exists.",
        # --- additional keys used by templates / app.js ---
        "open_sidebar": "Open sidebar",
        "close_sidebar_tt": "Close sidebar",
        "what_can_i_help": "What can I help with?",
        "disclaimer_hint": "5AI can make mistakes. Check important info.",
        "delete_tooltip": "Delete",
        "copy_code": "Copy",
        "copied": "Copied!",
        "clear_conversation_confirm": "Clear this conversation? This cannot be undone.",
        "chat_limit_reached": "You've reached the 40-chat limit. Delete an old chat to start a new one.",
        "no_account_prompt": "Don't have an account?",
        "register_action": "Register",
        "have_account_prompt": "Already have an account?",
        "login_action": "Log in",
        "create_account_subtitle": "Create a new account",
        "account_created_subtitle": "Account created. Sign in to continue",
        "something_went_wrong": "Something went wrong.",
        "cannot_reach_server": "Could not reach the server.",
        "error_reach_server": "Error: could not reach server",
        "error_connection_lost": "Error: connection lost",
    },
    "tr": {
        "app_name": "5AI",
        "sign_in_title": "5AI — Giriş Yap",
        "welcome_back": "Tekrar hoş geldiniz — devam etmek için giriş yapın",
        "username": "Kullanıcı adı",
        "password": "Şifre",
        "remember_me": "Beni hatırla",
        "log_in": "Giriş Yap",
        "no_account": "Hesabınız yok mu? Kayıt olun",
        "choose_username": "Bir kullanıcı adı seçin",
        "choose_password": "Bir şifre seçin",
        "confirm_password": "Şifreyi onaylayın",
        "create_account": "Hesap Oluştur",
        "have_account": "Zaten hesabınız var mı? Giriş yapın",
        "enter_both": "Lütfen kullanıcı adını ve şifreyi girin.",
        "fill_all_fields": "Lütfen tüm alanları doldurun.",
        "passwords_no_match": "Şifreler eşleşmiyor.",
        "invalid_credentials": "Geçersiz kullanıcı adı veya şifre.",
        "new_chat": "Yeni Sohbet",
        "new_chat_default_title": "Yeni sohbet",
        "settings": "Ayarlar",
        "log_out": "Çıkış yap",
        "delete_chat_tooltip": "Bu sohbeti sil",
        "delete_chat_title": "Sohbeti sil",
        "delete_chat_confirm": "Bu konuşma silinsin mi? Bu işlem geri alınamaz.",
        "typing": "5AI yazıyor…",
        "message_placeholder": "5AI'ye mesaj yaz…",
        "header_assistant": "5AI",
        "account_section": "HESAP",
        "signed_in_as": "Giriş yapan",
        "model_section": "YAPAY ZEKA MODELİ",
        "model_label": "Model",
        "language_section": "DİL",
        "language_label": "Uygulama dili",
        "english": "English",
        "turkish": "Türkçe",
        "actions_section": "İŞLEMLER",
        "clear_conversation": "Mevcut konuşmayı temizle",
        "close": "Kapat",
        "account_created": "Hesap başarıyla oluşturuldu.",
        "username_exists": "Bu kullanıcı adı zaten kullanılıyor.",
        # --- additional keys used by templates / app.js ---
        "open_sidebar": "Kenar çubuğunu aç",
        "close_sidebar_tt": "Kenar çubuğunu kapat",
        "what_can_i_help": "Bugün nasıl yardımcı olabilirim?",
        "disclaimer_hint": "5AI hata yapabilir. Önemli bilgileri kontrol edin.",
        "delete_tooltip": "Sil",
        "copy_code": "Kopyala",
        "copied": "Kopyalandı!",
        "clear_conversation_confirm": "Bu konuşma temizlensin mi? Bu işlem geri alınamaz.",
        "chat_limit_reached": "40 sohbet sınırına ulaştınız. Yeni bir sohbet başlatmak için eski bir sohbeti silin.",
        "no_account_prompt": "Hesabınız yok mu?",
        "register_action": "Kayıt ol",
        "have_account_prompt": "Zaten hesabınız var mı?",
        "login_action": "Giriş yap",
        "create_account_subtitle": "Yeni bir hesap oluştur",
        "account_created_subtitle": "Hesap oluşturuldu. Devam etmek için giriş yapın",
        "something_went_wrong": "Bir şeyler ters gitti.",
        "cannot_reach_server": "Sunucuya ulaşılamadı.",
        "error_reach_server": "Hata: sunucuya ulaşılamadı",
        "error_connection_lost": "Hata: bağlantı kesildi",
    },
}

DEFAULT_LANGUAGE = "en"
_current_language = DEFAULT_LANGUAGE


def set_language(lang: str):
    """Switch the active language. No-op if the language isn't supported."""
    global _current_language
    if lang in TRANSLATIONS:
        _current_language = lang


def get_language() -> str:
    return _current_language


def t(key: str) -> str:
    """Translate a key to the currently active language, falling back to
    English and then to the raw key if nothing is found."""
    lang_table = TRANSLATIONS.get(_current_language, TRANSLATIONS[DEFAULT_LANGUAGE])
    return lang_table.get(key, TRANSLATIONS[DEFAULT_LANGUAGE].get(key, key))


def get_translations(lang: str) -> dict:
    """Return the full key->string table for a given language (falls back
    to English for missing keys). Useful for handing the whole table to a
    template or serializing to JSON for the frontend, without touching the
    shared/global _current_language (safer under concurrent requests)."""
    base = dict(TRANSLATIONS[DEFAULT_LANGUAGE])
    base.update(TRANSLATIONS.get(lang, {}))
    return base


def translator(lang: str):
    """Return a per-request t(key) function bound to `lang`, without
    mutating global state."""
    table = get_translations(lang)

    def _t(key: str) -> str:
        return table.get(key, key)

    return _t
