import datetime
import re

from email_validator import EmailNotValidError, validate_email


def is_valid_email(email: str) -> bool:
    try:
        validate_email(email, check_deliverability=False)
        return True
    except EmailNotValidError:
        return False


"""
中国内地手机号段数据
数据来源：https://zh.wikipedia.org/wiki/中国内地移动终端通讯号段
更新日期：2019-04-27

---
修订记录：2020-05-15
修订参考：https://zh.wikipedia.org/w/index.php?title=%E4%B8%AD%E5%9B%BD%E5%86%85%E5%9C%B0%E7%A7%BB%E5%8A%A8%E7%BB%88%E7%AB%AF%E9%80%9A%E8%AE%AF%E5%8F%B7%E6%AE%B5&type=revision&diff=59486382&oldid=53664400
变化摘要：
* 移动新增：195， 197
* 联通新增：171， 196
* 电信新增：190， 193
* 中国广电：192
* 虚拟运营商：
  - 电信：162，170[012]
  - 联通：167，170[4789]
  - 移动：165，170[356]
---

---
修订记录：2020-11-05
变化摘要：
* 移动新增：172
注：资料 https://zh.wikipedia.org/w/index.php?title=%E4%B8%AD%E5%9B%BD%E5%86%85%E5%9C%B0%E7%A7%BB%E5%8A%A8%E7%BB%88%E7%AB%AF%E9%80%9A%E8%AE%AF%E5%8F%B7%E6%AE%B5&type=revision&diff=59486382&oldid=53664400  # noqa: E501
显示 172 为物联网号段。实际情况 172 号段确实有用户使用，且能打电话、发短信，因此现在将 172 号段添加进来。
---

中国移动： r'^(134|13[5-9]|147|15[0-27-9]|165|170|178|18[2-478]|19[578])[0-9]{8}$'
* 134[0-8] 为简化正则式，正则式中不对比第4位，即匹配 134*
* 13[5-9]
* 147
* 15[0-27-9]
* 165
* 170[356] 为简化正则式，正则式中不对比第四位，即匹配 170*
* 178
* 18[2-478]
* 19[578]

中国联通： r'^(13[0-2]|145|15[56]|16[67]|170|17[156]|18[56]|196)[0-9]{8}$'
* 13[0-2]
* 145
* 15[56]
* 16[67]
* 170[4789] 为简化正则式，正则式中不对比第四位，即匹配 170*
* 17[156]
* 18[56]
* 196

中国电信：r'^(133|149|153|162|170|17[37]]|18[019]|19[0139])[0-9]{8}$'
* 133
* 1349 卫星手机卡，不计入（综合里面为了方便会被计入）
* 149
* 153
* 162
* 170[012] 为简化正则式，正则式中不对比第四位，即匹配 170*
* 173
* 1740[0-5] 卫星手机卡，不计入
* 177
* 18[019]
* 19[0139]

中国广电：r'^(192)[0-9]{8}$'


综合： r'^(13[0-9]|14[579]|15[0-35-9]|16[2567]|17[0135-8]|18[0-9]|19[0-9])[0-9]{8}$'
* 13[0-9] 其中 1349 是卫星手机卡，这里为了方便也计入了
* 14[579]
* 15[0-35-9]
* 16[2567]
* 17[0135-8]
* 1740[0-5] 卫星手机卡，不计入
* 18[0-9]
* 19[0-9]
"""
_PHONE_PATTERN_CHINA_MOBILE = re.compile(r"^(134|13[5-9]|147|15[0-27-9]|165|170|172|178|18[2-478]|19[578])[0-9]{8}$")
_PHONE_PATTERN_CHINA_UNICOM = re.compile(r"^(13[0-2]|145|15[56]|16[67]|170|17[156]|18[56]|196)[0-9]{8}$")
_PHONE_PATTERN_CHINA_TELECOM = re.compile(r"^(133|149|153|162|170|17[37]]|18[019]|19[0139])[0-9]{8}$")
_PHONE_PATTERN_CHINA = re.compile(r"^(13[0-9]|14[579]|15[0-35-9]|16[2567]|17[01235-8]|18[0-9]|19[0-9])[0-9]{8}$")


def is_valid_phone(phone: str, allow_fake: bool = False) -> bool:
    """
    检查是否合法的中国内地手机号，返回 True/False
    """
    try:
        valid = bool(_PHONE_PATTERN_CHINA.match(phone))
        if not valid and allow_fake:
            return is_fake_phone(phone)
        return valid
    except TypeError:
        # 当 phone 不是字符串时，会抛出 TypeError
        return False


_FAKE_PHONE_PATTERN = re.compile(r"^100[0-9]{8}$")


def is_fake_phone(phone: str) -> bool:
    """
    在我们的体系中，我们使用 100 开头的号码作为假手机号。
    """
    try:
        return bool(_FAKE_PHONE_PATTERN.match(phone))
    except TypeError:
        return False


def is_valid_ric(number: str) -> bool:
    """
    检查身份证号是否合法，返回True/False
    参考： https://github.com/arthurdejong/python-stdnum
    主要修改：
        去掉了行政区划（身份证前6位）的校验，原因是参考库不全，且已有的校验已经基本能满足需求
    """
    # 如果长度！= 18或者15，则返回False
    # 我国第一代身份证是15位，于2013年1月1日正式退出
    if len(number) != 18 and len(number) != 15:
        return False

    # 校验生日
    if not is_valid_ric_birthday(number):
        return False

    # 第一代身份证没有尾数校验
    # 计算校验位：身份证最后一位数字要与前17位经过运算后的数字相等，否则返回False
    if len(number) == 18:
        try:
            checksum = (1 - 2 * int(number[:-1], 13)) % 11
        except ValueError:
            return False
        # 要求如果最后一位是字母 X，则必须是大写
        last_digit = "X" if checksum == 10 else str(checksum)
        if number[-1] != last_digit:
            return False

    return True


def is_valid_ric_birthday(number: str) -> bool:
    """
    出生日期的校验篇幅较长，这边单拎出来写，只能在is_valid_ric（）中调用此函数
    """
    # 获取年份
    # 第一代身份证出生年份用两位表示，且如果这两位数<=13，则在前面填充‘20’，因为1913年及出生以前的人（到现在107岁），应当不在实际场景中
    if len(number) == 15:
        try:
            if int(number[6:8]) <= 13:
                year = "20" + number[6:8]
            else:
                year = "19" + number[6:8]
        except TypeError:
            return False
    else:
        year = number[6:10]

    # 获取月份
    month = number[8:10] if len(number) == 15 else number[10:12]

    # 获取日期
    day = number[10:12] if len(number) == 15 else number[12:14]

    # 校验生日，非法日期返回False
    try:
        datetime.date(int(year), int(month), int(day))
    except ValueError:
        return False

    return True
