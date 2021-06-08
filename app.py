from flask import Flask, request, abort
from random import sample
from linebot import (LineBotApi, WebhookHandler)
from linebot.exceptions import (InvalidSignatureError)
from linebot.models import (
    FollowEvent,
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
        self.identity = "civilian"
        self.signal = ""
    def setIdentity(self ,identity):
        self.identity = identity
    def setISignal(self ,signal):
        self.signal = signal


#儲存房間的資料
class Room:
    def __init__(self, room_id):
        self.room_id = room_id
        self.players = []
        self.undercoverNum = 1
        self.undercovers = []
    def addPlayer(self, player):
        self.players.append(player)
    def showPlayers(self):
        str = "已經加入的玩家:\n"
        for player in self.players:
            str += player.name + '\n'
        return str
    #分配身分
    def setIdentities(self):
        self.undercovers = sample(self.players, self.undercoverNum)
        newSignal = Signal()
        for i in self.undercovers:
            i.setIdentity("undercover")
        #分配暗號
        for i in self.players:
            if i.identity == "civilian":
                i.setISignal(newSignal.civilian)
            else:
                i.setISignal(newSignal.undercover)

#暗號
class Signal:
    def __init__(self):
        self.civilian = "蝸牛"
        self.undercover = "烏龜"

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

# 接收 LINE 的資訊
@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)
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
    if event.source.type == "group":
        groupid = event.source.group_id
        roomIndex = findRoomIndex(groupid)
    profile = line_bot_api.get_profile(userid)
    userName = profile.display_name
    
    if event.message.text == "!help":
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="我是誰是臥底小幫手\n創建房間請輸入\t!create\n加入房間請輸入\t!join\n確認房間玩家請輸入\t!checkplayers"))

    if event.message.text == "!create":
        newRoom = Room(groupid)
        rooms.append(newRoom)
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="已創建新房間\n要加入房間前請先把小幫手加入好友\n加入房間請輸入 !join"))

    if event.message.text == "!join":
        newPlayer = Player(userName, userid)
        rooms[roomIndex].addPlayer(newPlayer)
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=userName + "已加入房間\n要開始遊戲請輸入 !start"))
        line_bot_api.push_message(userid, TextSendMessage(text="你已經成功加入房間\n請等待遊戲開始"))

    if event.message.text == "!checkplayers":
        reply = rooms[roomIndex].showPlayers()
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=reply))
    
    if event.message.text == "!start":
        rooms[roomIndex].setIdentities()
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="遊戲已經開始\n已經將暗號私訊給每個人囉~"))
        for player in rooms[roomIndex].players:
            line_bot_api.push_message(player.user_id, TextSendMessage(text="遊戲已經開始\n你拿到的暗號是: "+ player.signal))

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
    newcoming_text = "我是誰是臥底小幫手\n謝謝邀請我來此群組！\n想得到幫助請輸入!help"
    line_bot_api.reply_message(
            event.reply_token,
            TextMessage(text=newcoming_text)
        )

#加入好友時觸發的event
@handler.add(FollowEvent)
def handle_follow(event):
    newcoming_text = "我是誰是臥底小幫手\n謝謝把我加入好友！\n想得到幫助請輸入!help"
    line_bot_api.reply_message(
            event.reply_token,
            TextMessage(text=newcoming_text)
        )

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
