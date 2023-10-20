from io import BytesIO
from lxml import etree


def login_params(page_content):
    params = dict()
    parser = etree.HTMLParser()
    tree = etree.parse(BytesIO(page_content), parser=parser)
    for elem in tree.findall('//input'):
        name = elem.get('name')
        if name is not None:
            params[name] = elem.get('value', None)
    return params


def filled_login_params(login_page_content, login, password):
    token_params = login_params(login_page_content)
    value_map = {
        'login': login,
        'username': login,
        'password': password
                 }
    for key, value in token_params.items():
        for phrase, variable in value_map.items():
            if phrase in key.lower():
                token_params[key] = variable
    return token_params

