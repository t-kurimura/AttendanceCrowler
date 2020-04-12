
import re
import os
import urllib
from datetime import datetime, timedelta

from slack import WebClient

host = os.environ['HOST']
token = os.environ['SLACK_TOKEN']
channel = os.environ['SLACK_CHANNEL']
bot_token = token


def __search_messages(query):
    message_list = []

    s_quote = urllib.parse.quote(query)
    client = WebClient(token=token)

    for i in range(0, 100):
        data = client.search_messages(query=s_quote, page=i, sort="timestamp", sort_dir="asc")
        # print(data.data['ok'], data.data["messages"]["paging"]["pages"], data.data["messages"]["paging"]["page"])

        message_list.extend(data.data["messages"]["matches"])
        if data.data["messages"]["paging"]["pages"] == 0:
            print("could not find")
            break
        if data.data["messages"]["paging"]["pages"] == data.data["messages"]["paging"]["page"]:
            break

    return message_list


def __convert_to_dict(response_dict_list):
    msg_array = []
    msg_dict = {
        'ts': [],
        'parent_ts': [],
        'is_parent': [],
        'text': [],
        'permalink': [],
    }

    for elm in response_dict_list:
        m = re.search('[0-9]*\.[0-9]*$', elm["permalink"])
        parent_ts = 0
        if m is not None:
            parent_ts = m.group(0)

        msg_dict['ts'].append(datetime.fromtimestamp(float(elm["ts"])))
        msg_dict['parent_ts'].append(datetime.fromtimestamp(float(parent_ts)))
        msg_dict['is_parent'].append(elm["ts"] == parent_ts)
        msg_dict['text'].append(elm["text"])
        msg_dict['permalink'].append(elm["permalink"])

        msg_array.append({
            'ts': datetime.fromtimestamp(float(elm["ts"])),
            'parent_ts': datetime.fromtimestamp(float(parent_ts)),
            'is_parent': elm["ts"] == parent_ts,
            'text': elm["text"],
            'permalink': elm["permalink"],
        })

    result = []
    for i in msg_array:
        if i['parent_ts'] in msg_dict['ts']:
            i['ts']=i['ts']
            result.append(i)
    



    return result


def output(msg_array):
    each_str = []
    for i in msg_array:
        each_str.append("{} {}".format(
            datetime.strftime(i['ts'], "%H:%M"),
            re.sub(r'@', '[at]', re.sub(r'<.*\||\n|>', '', i['text'])),
        ))
    return "\n".join(each_str)


def post_image(path):
    client = WebClient(token=bot_token)
    response = client.files_upload(
        token=token,
        channels=channel,
        file=path,
    )
    print(response)


def post_with_attachment(
        start_tm: datetime,
        end_tm: datetime,
        log: str
):
    attachment = [
            {
                "fallback": "Required plain-text summary of the attachment.",
                "color": "#000000",
                "mrkdwn_in": [
                    "fields",
                    "text"
                ],
                "title": start_tm.strftime("%Y月%m月%d日"),
                "author_name": "出退勤編集",
                "author_link": "https://{}/employee/attendance/edit".format(host),
        
                "fields": [
                    {
                        "title": "出勤時刻",
                        "value": start_tm.strftime("%H:%M"),
                        "short": True
                    },
                    {
                        "title": "退勤時刻",
                        "value": end_tm.strftime("%H:%M"),
                        "short": True
                    },
                    {
                        "title": "休憩時間",
                        "value": "01:00",
                        "short": True
                    },
                    {
                        "title": "#Attendance",
                        "value": log,
                        "short": False
                    }
                ]
            }
        ]

    client = WebClient(token=bot_token)
    response = client.chat_postMessage(
        channel=channel,
        text="出退勤を保存しました",
        attachments=attachment,
        as_user=True,
    )
    print(response)


def get_target_date_attendance_post(
        user_id,
        start_dt,
        end_dt,

):
    query = "in:#eureka-attendance after:{} before:{} from:@{}".format(
        (start_dt - timedelta(days=1)).strftime("%Y-%m-%d"),
        (end_dt + timedelta(days=1)).strftime("%Y-%m-%d"),
        user_id
    )
    print(query)
    msg_response_dict = __search_messages(query)
    return __convert_to_dict(msg_response_dict)
