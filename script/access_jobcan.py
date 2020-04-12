#!/usr/local/bin/python3
import os
import re
import datetime
from time import sleep

from selenium import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

import search_slack

base_row_path = "#search-result > form > table.non-frame > tbody > tr > td > table > tbody > tr:nth-child({})"
date_cell_selector = " {} > td:nth-child(4)".format(base_row_path)
is_holiday_selector = " {} > td:nth-child(7)".format(base_row_path)
start_time_selector = " {} > td:nth-child(10)> #editable_start > input[type=text]".format(base_row_path)
end_time_selector = " {} > td:nth-child(11)> #editable_end > input[type=text]".format(base_row_path)
rest_duration_selector = " {} > td:nth-child(12) >  #editable_rest > input[type=text]".format(base_row_path)
appendix_selector = " {} > td:nth-child(17) > #editable_memo > textarea".format(base_row_path)


def get_empty_dates(access_browser: webdriver):
    host = os.environ['HOST']
    access_browser.get('https://{}/login/pc-employee/old?lang_code=ja'.format(host))
    sleep(5)

    company_id = access_browser.find_element_by_id("client_id")
    company_id.send_keys(os.environ['CLIENT_ID'])

    email = access_browser.find_element_by_id("email")
    email.send_keys(os.environ['EMAIL'])

    password = access_browser.find_element_by_id("password")
    password.send_keys(os.environ['PASSWORD'])

    login_button = access_browser.find_element_by_css_selector(
        "body > div > div > div.login-block > form:nth-child(3) > div:nth-child(5) > button")
    login_button.click()
    sleep(10)

    access_browser.get("https://{}/employee/attendance/edit".format(host))
    sleep(5)

    empty_dates = []
    for i in list(range(2, 35)):
        raw_date_str = access_browser.find_element_by_css_selector(date_cell_selector.format(i)).text
        date_str = re.search(r'[0-9]{2}/[0-9]{2}', raw_date_str).group(0)
        target_date = datetime.datetime.strptime(
            "{}/{} 23:59".format(
                datetime.datetime.now().strftime("%Y"),
                date_str
            ),
            "%Y/%m/%d %H:%M",
        )
        if target_date > datetime.datetime.now():
            break

        raw_holiday_str = access_browser.find_element_by_css_selector(is_holiday_selector.format(i)).text
        if len(re.sub(r'\s', '', raw_holiday_str)) > 0:
            continue

        start_time_str = access_browser.find_element_by_css_selector(start_time_selector.format(i)).get_attribute(
            "value")
        end_time_str = access_browser.find_element_by_css_selector(end_time_selector.format(i)).get_attribute("value")
        rest_time_str = access_browser.find_element_by_css_selector(rest_duration_selector.format(i)).get_attribute(
            "value")
        has_empty = (
                            len(re.sub(r'\s', '', start_time_str)) *
                            len(re.sub(r'\s', '', end_time_str)) *
                            len(re.sub(r'\s', '', rest_time_str))
                    ) == 0
        if not has_empty:
            continue

        empty_dates.append(target_date)
    return empty_dates


def fill_empty(access_browser, result):
    for i in list(range(2, 35)):
        raw_date_str = access_browser.find_element_by_css_selector(date_cell_selector.format(i)).text
        date_str = re.search(r'[0-9]{2}/[0-9]{2}', raw_date_str).group(0)
        target_date = datetime.datetime.strptime(
            "{}/{} 23:59".format(
                datetime.datetime.now().strftime("%Y"),
                date_str
            ),
            "%Y/%m/%d %H:%M",
        )
        if target_date > datetime.datetime.now():
            break

        raw_holiday_str = access_browser.find_element_by_css_selector(is_holiday_selector.format(i)).text
        if len(re.sub(r'\s', '', raw_holiday_str)) > 0:
            continue

        duration_dict = result.get(target_date)
        if duration_dict is None:
            continue

        start = access_browser.find_element_by_css_selector(start_time_selector.format(i))
        start.clear()
        start.send_keys(duration_dict["start_time"].strftime("%H:%M"))

        end = access_browser.find_element_by_css_selector(end_time_selector.format(i))
        end.clear()
        end.send_keys(duration_dict["end_time"].strftime("%H:%M"))

        rest = access_browser.find_element_by_css_selector(rest_duration_selector.format(i))
        rest.clear()
        rest.send_keys("01:00")

        appndix = access_browser.find_element_by_css_selector(appendix_selector.format(i))
        appndix.clear()
        appndix.send_keys(duration_dict["permalink"])

        save_button = access_browser.find_element_by_css_selector(
            "#search-result > form > table:nth-child(3) > tbody > tr > td:nth-child(2) > div")
        save_button.click()
        sleep(1)

    # スクリーンショット
    dt = datetime.datetime.today()
    dtstr = dt.strftime("%Y%m%d%H%M%S")
    path = '/root/script/images/' + dtstr + '.png'
    access_browser.save_screenshot(path)
    return path


if __name__ == '__main__':
    try:
        # HEADLESSブラウザに接続
        print("接続")
        browser = webdriver.Remote(
            command_executor='http://selenium-hub:4444/wd/hub',
            desired_capabilities=DesiredCapabilities.CHROME)
        browser.set_window_size(1260, 2300)

        # 空白の日付を集める
        print("日付収集")
        empty_date_list = get_empty_dates(browser)

        # 特定の日付の発言を集める
        print("発言収集")
        date_posts_set = {}
        for ask_date in empty_date_list:
            print("---1")
            print(ask_date)
            posts = search_slack.get_target_date_attendance_post(
                user_id="WDW4S1NTG",
                start_dt=ask_date,
                end_dt=ask_date,
            )
            if len(posts) <= 1:
                continue
            
            print("---2")
            duration = {
                'start_time': posts[0]['ts'],
                'end_time': posts[len(posts) - 1]['ts'],
                'permalink': posts[0]['permalink'],
            }
            date_posts_set[ask_date] = duration

            search_slack.post_with_attachment(
                posts[0]['ts'],
                posts[len(posts) - 1]['ts'],
                search_slack.output(posts)
            )

        # 埋めるi
        print("埋めるcheck")
        image_path = None
        if len(date_posts_set) > 0:
            print("埋める")
            image_path = fill_empty(browser, date_posts_set)

        # 結果を出力
        if image_path is not None:
            print("出力")
            search_slack.post_image(image_path)
        
        if image_path is not None: 
            print("削除")
            os.remove(image_path)

    finally:
        # 終了
        browser.close()
        browser.quit()
