from flask import Flask, request, abort
from random import (sample, shuffle)
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
    TemplateSendMessage,
    ButtonsTemplate,
    MessageTemplateAction,
    PostbackEvent,
    PostbackTemplateAction,
    PostbackAction, ImagemapSendMessage, ImageSendMessage, StickerSendMessage, AudioSendMessage, LocationSendMessage,
    FlexSendMessage, VideoSendMessage,
)
from linebot.models.events import JoinEvent, PostbackEvent, MemberJoinedEvent, MemberLeftEvent

import os

import pandas as pd

from requests import NullHandler

# 儲存加入玩家的資料


class Player:
    def __init__(self, name, user_id):
        self.name = name
        self.user_id = user_id
        self.identity = "civilian"
        self.signal = ""
        self.isDie = False
        self.voteNum = 0

    def setIdentity(self, identity):
        self.identity = identity

    def setISignal(self, signal):
        self.signal = signal


# 儲存房間的資料
class Room:
    def __init__(self, room_id):
        self.room_id = room_id
        self.players = []
        self.undercoverNum = 1
        self.undercovers = []
        self.survives = []
        self.surviveUndercover = 0
        self.surviveCivilian = 0
        self.state = 1      # 1:創建房間 2:遊戲開始 3:開始投票 4:公布投票結果
        self.isVote = 0

    def addPlayer(self, player):
        self.players.append(player)

    def showPlayers(self):
        str = ""
        for i, player in enumerate(self.players):
            str += player.name
            if i != len(self.players)-1:
                str += '\n'
        return str

    def showSurvives(self):
        str = ""
        for i, player in enumerate(self.survives):
            str += player.name
            if i != len(self.survives)-1:
                str += '\n'
        return str

    def setState(self, state):
        self.state = state
    # 遊戲開始時分配身分

    def setIdentities(self):
        self.undercovers = sample(self.players, self.undercoverNum)
        newSignal = Signal()
        for i in self.undercovers:
            i.setIdentity("undercover")
        # 打亂順序
        shuffle(self.players)
        # 分配暗號
        for i in self.players:
            if i.identity == "civilian":
                i.setISignal(newSignal.civilian)
            else:
                i.setISignal(newSignal.undercover)
    # 檢查房間內有無這人

    def hasPlayer(self, user_id):
        ret = False
        for i in self.players:
            if i.user_id == user_id:
                ret = True
        return ret
    # 檢查活人

    def findSurvive(self):
        self.survives.clear()
        for i in self.players:
            if i.isDie == False:
                self.survives.append(i)
        self.surviveCivilian = 0
        self.surviveUndercover = 0
        for i in self.survives:
            if i.identity == "civilian":
                self.surviveCivilian += 1
            else:
                self.surviveUndercover += 1


# 暗號
class Signal:
    def __init__(self):
        pair_table = pd.read_excel(
            'who_is_under_cover.xlsx', engine='openpyxl')
        single_row = pair_table.sample()
        self.civilian = single_row['civilian'].values[0]
        self.undercover = single_row['under_cover'].values[0]


app = Flask(__name__)

line_bot_api = LineBotApi(
    '3dl/t0sL0uKA2/vt0fACm5FgMnP6Ba4bVE89258SDraqlkq355fff824TVW3WvIHVSEYCWbhv6A38oNcOue/R8u2orOreInHietxvPlg3SzjbQIbK/osq3xQc4QHLDI0hHXaV5NcWSWHR/wXeCOpSwdB04t89/1O/w1cDnyilFU=')
handler = WebhookHandler('b7982d4e833c3efb4a5ac372b52b441d')
rooms = []


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

# 輸入文字時觸發的event


@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    userid = event.source.user_id
    if event.source.type == "group":
        groupid = event.source.group_id
        roomIndex = findRoomIndex(groupid)
        if roomIndex != -1:
            room = rooms[roomIndex]
    profile = line_bot_api.get_profile(userid)
    userName = profile.display_name

    # 尋求幫助
    if event.message.text == "!help":
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="我是誰是臥底小幫手\n創建房間請輸入\t!create\n加入房間請輸入\t!join\n確認房間玩家請輸入\t!checkplayers"))

    # 創建房間
    if event.message.text == "!create":
        newRoom = Room(groupid)
        rooms.append(newRoom)
        buttons_template = TemplateSendMessage(
            alt_text='Buttons Template',
            template=ButtonsTemplate(
                title='已創建新房間',
                text="想參與遊戲前請先把小幫手加入好友\n加入好友後請按「加入房間」",
                actions=[
                    MessageTemplateAction(
                        label="加入房間",
                        text="!join"
                    ),
                    MessageTemplateAction(
                        label="解散房間",
                        text="!disband"
                    )
                ]
            )
        )
        line_bot_api.reply_message(
            event.reply_token,
            buttons_template)

    # 加入房間
    if event.message.text == "!join":
        if room.state != 1:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=userName + "遊戲早就開始囉\n請等待下一局開始"))
        elif room.hasPlayer(userid) == True:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=userName + "你原本就在房間內囉"))
        else:
            newPlayer = Player(userName, userid)
            room.addPlayer(newPlayer)
            buttons_template = TemplateSendMessage(
                alt_text='Buttons Template',
                template=ButtonsTemplate(
                    title=userName + "已加入房間",
                    text="所有玩家準備就緒時請按「開始遊戲」\n想離開房間請按「退出房間」",
                    actions=[
                        MessageTemplateAction(
                            label="開始遊戲",
                            text="!start"
                        ),
                        MessageTemplateAction(
                            label="退出房間",
                            text="!leave"
                        ),
                        MessageTemplateAction(
                            label="查看房間玩家",
                            text="!checkplayers"
                        )
                    ]
                )
            )
            line_bot_api.reply_message(
                event.reply_token,
                buttons_template)
            line_bot_api.push_message(
                userid, TextSendMessage(text="你已經成功加入房間\n請等待遊戲開始"))

    #解散房間
    if event.message.text == "!disband":
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="房間已解散"))
        rooms.remove(room)

    #退出房間
    if event.message.text == "!leave":
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text= (userName + "已離開房間")))
        room.players.remove(findWhichPlayer(userid))

    # 查詢房間玩家
    if event.message.text == "!checkplayers":
        reply = "已經加入的玩家:\n" + room.showPlayers()
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=reply))

    # 開始遊戲
    if event.message.text == "!start":
        if room.state != 1:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="遊戲早就開始囉"))
        else:
            room.setState(2)
            room.setIdentities()
            reply = "遊戲已經開始\n已經將暗號私訊給每個人囉~\n請按照以下順序描述你拿到的暗號:\n" + room.showPlayers()
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=reply))
            
            buttons_template = TemplateSendMessage(
                alt_text='Buttons Template',
                template=ButtonsTemplate(
                    title='投票',
                    text="描述完畢請按「開始投票」",
                    actions=[
                        MessageTemplateAction(
                            label="開始投票",
                            text="!vote"
                        )
                    ]
                )
            )
            line_bot_api.push_message(
                room.room_id,
                buttons_template)

            for player in room.players:
                line_bot_api.push_message(player.user_id, TextSendMessage(
                    text="遊戲已經開始\n你拿到的暗號是: " + player.signal+"\n請到群組輪流描述你拿到的暗號"))

    # 投票階段
    if event.message.text == "!vote":
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="進入投票階段\n請各位到私訊窗選出最可疑的嫌疑犯"))
        room.findSurvive()
        options = []
        for i in room.survives:
            options.append(PostbackTemplateAction(
                label=i.name,
                text=i.name,
                data="vote" + i.user_id
            )
            )
        for i in room.survives:
            buttons_template = TemplateSendMessage(
                alt_text='Buttons Template',
                template=ButtonsTemplate(
                    title='投票',
                    text="以下是目前還存活的玩家\n請選出可疑的嫌疑犯",
                    actions=options
                )
            )
            line_bot_api.push_message(i.user_id, buttons_template)

# 處理私訊的投票


@handler.add(PostbackEvent)
def handle_postback(event):
    if event.postback.data[0:4] == "vote":
        user_id = event.postback.data[4:]
        print(event.postback.data + "\n" + user_id)
        candidate = findWhichPlayer(user_id)
        candidate.voteNum += 1
        room = rooms[findWhichRoom(user_id)]
        room.isVote += 1
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="你投給了" + candidate.name + "\n請稍等其他玩家"))
        # 結算投票
        if room.isVote >= len(room.survives):
            for player in room.survives:
                line_bot_api.push_message(
                    player.user_id, TextSendMessage(text="所有人都已投票完畢\n請至群組察看結果"))
            reply = "公布投票結果:\n"
            highestPlayer = candidate
            for player in room.survives:
                reply += player.name + str(player.voteNum) + "票\n"
                if player.voteNum > highestPlayer.voteNum:
                    highestPlayer = player
            reply += ("最高票為: " + highestPlayer.name + "\n大家決定處決掉他\n" + highestPlayer.name + "的身分是: ")
            if highestPlayer.identity == "civilian":
                reply += "平民"
            else:
                reply += "臥底"
            line_bot_api.push_message(room.room_id, TextSendMessage(text = reply))
            highestPlayer.isDie = True
            room.findSurvive()
            # 判斷遊戲勝負
            if room.surviveUndercover == 0:
                line_bot_api.push_message(room.room_id, TextSendMessage(
                    text="平民尚餘" + str(room.surviveCivilian) + "人\n臥底尚餘" + str(room.surviveUndercover) + "人\n平民獲勝\n遊戲結束"))
                rooms.remove(room)
            elif room.surviveCivilian <= room.surviveUndercover:
                line_bot_api.push_message(room.room_id, TextSendMessage(
                    text="平民尚餘" + str(room.surviveCivilian) + "人\n臥底尚餘" + str(room.surviveUndercover) + "人\n臥底獲勝\n遊戲結束"))
                rooms.remove(room)
            else:
                line_bot_api.push_message(room.room_id, TextSendMessage(
                    text="平民尚餘" + str(room.surviveCivilian) + "人\n臥底尚餘" + str(room.surviveUndercover) + "人\n遊戲繼續"))
                line_bot_api.push_message(room.room_id, TextSendMessage(
                    text="請按照以下順序描述你拿到的暗號:\n" + str(room.showSurvives()) + "描述完畢請輸入 !vote開始投票"))


# 找到房間的index
def findRoomIndex(group_id):
    roomIndex = -1
    for i, room in enumerate(rooms):
        if room.room_id == group_id:
            roomIndex = i
    return roomIndex

# 根據user_id找到玩家是誰
def findWhichPlayer(user_id):
    for room in rooms:
        for player in room.players:
            if player.user_id == user_id:
                return player
    return -1

# 根據user_id找到玩家在哪一間room
def findWhichRoom(user_id):
    for i, room in enumerate(rooms):
        for player in room.players:
            if player.user_id == user_id:
                return i
    return -1

# 邀請至群組時觸發的event
@handler.add(JoinEvent)
def handle_join(event):
    newcoming_text = "我是誰是臥底小幫手\n謝謝邀請我來此群組！\n想得到幫助請輸入!help"
    line_bot_api.reply_message(
        event.reply_token,
        TextMessage(text=newcoming_text)
    )

# 加入好友時觸發的event
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
