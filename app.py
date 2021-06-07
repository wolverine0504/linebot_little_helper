from flask import Flask, request, abort
from linebot import (LineBotApi, WebhookHandler)
from linebot.exceptions import (InvalidSignatureError)
from linebot.models import (
    JoinEvent,
    MessageEvent,
    TextMessage,
    TextSendMessage,
    TemplateSendMessage,
    QuickReply,
    QuickReplyButton,
    MessageAction,
    PostbackAction, ImagemapSendMessage, ImageSendMessage, StickerSendMessage, AudioSendMessage, LocationSendMessage,
    FlexSendMessage, VideoSendMessage,
)
from linebot.models.events import JoinEvent, PostbackEvent,MemberJoinedEvent,MemberLeftEvent

import os

#儲存加入玩家的資料
class Player:
    def __init__(self, name, user_id):
        self.name = name
        self.user_id = user_id

#儲存房間的資料
class Room:
    def __init__(self, room_id):
        self.room_id = room_id
        self.players = []
    def addPlayer(self, player):
        self.players.append(player)
    def showPlayers(self):
        str = "已經加入的玩家:\n"
        for player in self.players:
            str += player.name + '\n'
        return str

app = Flask(__name__)

line_bot_api = LineBotApi('3dl/t0sL0uKA2/vt0fACm5FgMnP6Ba4bVE89258SDraqlkq355fff824TVW3WvIHVSEYCWbhv6A38oNcOue/R8u2orOreInHietxvPlg3SzjbQIbK/osq3xQc4QHLDI0hHXaV5NcWSWHR/wXeCOpSwdB04t89/1O/w1cDnyilFU=')
handler = WebhookHandler('b7982d4e833c3efb4a5ac372b52b441d')
rooms= []

def getMessageObject(jsonObject):
    message_type = jsonObject.get('type')
    if message_type == 'text':
        return TextSendMessage.new_from_json_dict(jsonObject)
    elif message_type == 'imagemap':
        return ImagemapSendMessage.new_from_json_dict(jsonObject)
    elif message_type == 'template':
        return TemplateSendMessage.new_from_json_dict(jsonObject)
    elif message_type == 'image':
        return ImageSendMessage.new_from_json_dict(jsonObject)
    elif message_type == 'sticker':
        return StickerSendMessage.new_from_json_dict(jsonObject)
    elif message_type == 'audio':
        return AudioSendMessage.new_from_json_dict(jsonObject)
    elif message_type == 'location':
        return LocationSendMessage.new_from_json_dict(jsonObject)
    elif message_type == 'flex':
        return FlexSendMessage.new_from_json_dict(jsonObject)
    elif message_type == 'video':
        return VideoSendMessage.new_from_json_dict(jsonObject)



@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        print("Invalid signature. Please check your channel access token/channel secret.")
        abort(400)

    return 'OK'

#輸入文字時觸發的event
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    userid = event.source.user_id
    profile = line_bot_api.get_profile(userid)
    roomIndex = findRoomIndex(event.source.group_id)
    if event.message.text == "!help":
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="我是誰是臥底小幫手\n創建房間請輸入\t!create\n加入房間請輸入\t!join\n確認房間玩家請輸入\t!checkplayers"))

    if event.message.text == "!create":
        newRoom = Room(event.source.group_id)
        rooms.append(newRoom)
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="已創建新房間\nGroup id: "+event.source.group_id))

    if event.message.text == "!join":
        newPlayer = Player(profile.display_name, event.source.user_id)
        rooms[roomIndex].addPlayer(newPlayer)
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=profile.display_name+"已加入房間"))

    if event.message.text == "!checkplayers":
        reply = rooms[roomIndex].showPlayers()
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=reply))
    
#找到房間的index
def findRoomIndex(group_id):
    roomIndex = -1
    for i, room in enumerate(rooms):
        if room.room_id == group_id:
            roomIndex = i
    return roomIndex

#邀請至群組時觸發的event
@handler.add(JoinEvent)
def handle_join(event):
    newcoming_text = "我是誰是臥底小幫手\n謝謝邀請我這個機器來此群組！\n想知道自己的名字請輸入!name"
    line_bot_api.reply_message(
            event.reply_token,
            TextMessage(text=newcoming_text)
        )

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
