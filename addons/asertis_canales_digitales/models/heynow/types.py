from enum import Enum


class HeynowChannelType(Enum):
    WHATSAPP = 1
    FACEBOOK_MESSENGER = 2
    TWITTER = 3
    WEB_CHAT = 4
    FACEBOOK_WALL = 5
    WAVY = 6
    INSTAGRAM = 7
    MERCADO_LIBRE = 8
    SINCH = 9
    MERCADO_LIBRE_MENSAJES = 10
    CALL = 11
    PS_TWILIO = 12
    PS_YOUTUBE = 13
    PS_SMOOCH_WSP = 14
    PS_TWITTER_DM = 15
    PS_INSTAGRAM = 16
    PS_WAVY = 17
    PS_TWITTER = 18
    PS_WABOX = 19
    PS_MESSENGER = 20
    PS_ONEMARKETER = 21
    PS_TWITTER_TWEET = 22
    PS_FEED = 23
    TWITTER_DM = 24
    GOOGLE_BUSINESS_MESSAGES = 25
    MERCADO_LIBRE_RECLAMOS = 26
    BOTMAKER = 27
    TEAMS = 28
    TELEGRAM = 29
    API_CHANNEL = 30
    INSTAGRAM_DIRECT = 31
    SINCH_SMS = 32
    DIALOG_360 = 33
    TWILIO = 34
    WHATSAPP_CLOUD = 35
    GUPSHUP = 36
    HEY_TEST_CHANNEL = 37
    T2_VOICE = 38
    MAILBOT = 39
    FLOW_SERVICE = 40

    def etiqueta(self):
        etiquetas = {
            self.WHATSAPP: "WhatsApp",
            self.FACEBOOK_MESSENGER: "Facebook Messenger",
            self.TWITTER: "Twitter",
            self.WEB_CHAT: "Web Chat",
            self.FACEBOOK_WALL: "Facebook Muro",
            self.WAVY: "Wavy",
            self.INSTAGRAM: "Instagram",
            self.MERCADO_LIBRE: "Mercado Libre",
            self.SINCH: "Sinch",
            self.MERCADO_LIBRE_MENSAJES: "Mercado Libre (Mensajes)",
            self.CALL: "Call",
            self.PS_TWILIO: "ps_twilio",
            self.PS_YOUTUBE: "ps_youtube",
            self.PS_SMOOCH_WSP: "ps_smooch-wsp",
            self.PS_TWITTER_DM: "ps_twitterDM",
            self.PS_INSTAGRAM: "ps_instagram",
            self.PS_WAVY: "ps_wavy",
            self.PS_TWITTER: "ps_twitter",
            self.PS_WABOX: "ps_wabox",
            self.PS_MESSENGER: "ps_messenger",
            self.PS_ONEMARKETER: "ps_onemarketer",
            self.PS_TWITTER_TWEET: "ps_twitterTweet",
            self.PS_FEED: "ps_feed",
            self.TWITTER_DM: "Twitter DM",
            self.GOOGLE_BUSINESS_MESSAGES: "Google Business Messages",
            self.MERCADO_LIBRE_RECLAMOS: "Mercado Libre Reclamos",
            self.BOTMAKER: "Botmaker",
            self.TEAMS: "Teams",
            self.TELEGRAM: "Telegram",
            self.API_CHANNEL: "ApiChannel",
            self.INSTAGRAM_DIRECT: "Instagram",
            self.SINCH_SMS: "SinchSMS",
            self.DIALOG_360: "360Dialog",
            self.TWILIO: "twilio",
            self.WHATSAPP_CLOUD: "WhatsApp",
            self.GUPSHUP: "gupshup",
            self.HEY_TEST_CHANNEL: "HeyTestChannel",
            self.T2_VOICE: "T2Voice",
            self.MAILBOT: "MailBot",
            self.FLOW_SERVICE: "Flow Service",
        }
        return etiquetas.get(self, "Desconocido")

    def icon_name(self) -> str:
        """
        Devuelve el icono por defecto asociado al canal.
        """
        name_icon_formatter = {
            self.WHATSAPP: "whatsapp",
            self.WHATSAPP_CLOUD: "whatsapp",
            self.FACEBOOK_MESSENGER: "messenger",
            self.TWITTER: "twitter",
            self.WEB_CHAT: "webchat",
            self.FACEBOOK_WALL: "facebook",
            self.WAVY: "wavy",
            self.INSTAGRAM: "instagram",
            self.MERCADO_LIBRE: "mercadolibre",
            self.SINCH: "sinch",
            self.MERCADO_LIBRE_MENSAJES: "mercadolibre",
            self.CALL: "call",
            self.PS_TWILIO: "twilio",
            self.PS_YOUTUBE: "youtube",
            self.PS_SMOOCH_WSP: "generic",
            self.PS_TWITTER_DM: "twitter",
            self.PS_INSTAGRAM: "instagram",
            self.PS_WAVY: "wavy",
            self.PS_TWITTER: "twitter",
            self.PS_WABOX: "wabox",
            self.PS_MESSENGER: "messenger",
            self.PS_ONEMARKETER: "onemarketer",
            self.PS_TWITTER_TWEET: "twitter",
            self.PS_FEED: "feed",
            self.TWITTER_DM: "twitter",
            self.GOOGLE_BUSINESS_MESSAGES: "google",
            self.MERCADO_LIBRE_RECLAMOS: "mercadolibre",
            self.BOTMAKER: "botmaker",
            self.TEAMS: "teams",
            self.TELEGRAM: "telegram",
            self.API_CHANNEL: "api_channel",
            self.INSTAGRAM_DIRECT: "instagram",
            self.SINCH_SMS: "sms",
            self.DIALOG_360: "360dialog",
            self.TWILIO: "twilio",
            self.WHATSAPP_CLOUD: "whatsapp",
            self.GUPSHUP: "gupshup",
            self.HEY_TEST_CHANNEL: "chatbot",
            self.T2_VOICE: "chatbot",
            self.MAILBOT: "email",
            self.FLOW_SERVICE: "chatbot",
        }
        return name_icon_formatter.get(self, "generic")

    @classmethod
    def from_int(cls, valor: int) -> str:
        try:
            return cls(valor).etiqueta()
        except ValueError:
            return "Desconocido"
