import argparse
import re
from progress.bar import Bar
import pathlib
import urllib
from datetime import datetime
import requests
import validators
import logging


def remove_directory_tree(path):
    for child in path.glob('*'):
        if child.is_file():
            child.unlink()
        else:
            remove_directory_tree(child)
    path.rmdir()


def extract_local_asset_urls(html):
    asset_urls = []

    srcs = re.findall(r'src=(("(.*?)")|(\'(.*?)\'))', html)
    for group in srcs:
        if group[2] != '':
            asset_urls.append(group[2])
        elif group[4] != '':
            asset_urls.append(group[4])

    srcsets = re.findall(r'srcset=(("(.*?)")|(\'(.*?)\'))', html)
    for group in srcsets:
        if group[2] != '':
            asset_urls.append(group[2])
        elif group[4] != '':
            asset_urls.append(group[4])

    tag_links = re.findall(r'<link(.*?)href=(("(.*?)")|(\'(.*?)\'))', html)
    for group in tag_links:
        if group[3] != '':
            asset_urls.append(group[3])
        elif group[5] != '':
            asset_urls.append(group[5])

    return list(filter(lambda asset_url: asset_url[0] == '/', asset_urls))


def is_valid_link(group):
    link = ''
    if group[3] != '':
        link = group[3]
    elif group[5] != '':
        link = group[5]

    if link.startswith('javascript:void'):
        return False
    if link == '#':
        return False
    return True


def archive(url, include_metadata):
    if not validators.url(url):
        logging.error(f'{url} is not a valid URL.')
        return
    try:
        logging.info(f'{url} is being archived')
        headers={
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_7_3) AppleWebKit/537.36 (KHTML, like Gecko, Mediapartners-Google) Chrome/117.0.5938.132 Safari/537.3',
        }
        session = requests.Session()
        response = session.get(url, headers=headers)
        html = re.sub(r'\s', ' ', response.text)
        html = re.sub(r'\s+', ' ', html)
        cwd = pathlib.Path.cwd()
        web_page_url = re.sub(r'https?:\/\/', '', url)
        web_page_url = urllib.parse.quote(web_page_url, safe='')
        web_page_folder = cwd / web_page_url
        if web_page_folder.exists():
            remove_directory_tree(web_page_folder)
        web_page_folder.mkdir()
        web_page_html = web_page_folder / f'{web_page_url}.html'
        parsed_url = urllib.parse.urlparse(url)
        domain = f'{parsed_url.scheme}://{parsed_url.netloc}'
        local_asset_urls = extract_local_asset_urls(html)
        with Bar('Archiving', max=len(local_asset_urls), suffix='%(percent).1f%% - %(eta)ds') as bar:
            for asset_url in local_asset_urls:
                file_name = asset_url.split('/')[-1]
                file_name = file_name.split('?')[0]
                asset_dirs = asset_url.split('/')[1:-1]
                asset_path = pathlib.Path(web_page_folder, '/'.join(asset_dirs))
                asset_path.mkdir(parents=True, exist_ok=True)
                asset = session.get(domain + asset_url, headers=headers).content
                asset_file = asset_path / file_name
                asset_file.write_bytes(asset)
                html = html.replace(asset_url, asset_url[1:])
                bar.next()

        web_page_html.write_text(html)

        if include_metadata:
            images = re.findall(r'<img', html)
            tag_a = re.findall(r'<a(.*?)href=(("(.*?)")|(\'(.*?)\'))', html)
            links = list(filter(lambda group: is_valid_link(group), tag_a))
            now = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
            metadata = f'''METADATA
===============================================================================
Web page url: {url}
Local assets: {len(local_asset_urls)}
Number of images: {len(images)}
Number of links: {len(links)}
Archived date: {now}
'''
            logging.info(metadata)
            metadata_file = web_page_folder / 'metadata.txt'
            metadata_file.write_text(metadata)

        logging.info(f'{url} is archived successfully!\n')
        return True
    except Exception as e:
        logging.error(f'An error occured while archiving {url}!\n')
        logging.error(e)
        return False


if __name__ == '__main__':
    arg_parser = argparse.ArgumentParser(
        prog='WebPageArchiver',
        description='Archives the web page contents from the given list of urls',
    )
    arg_parser.add_argument('-m', '--metadata',
                            action='store_true',
                            help='include metadata')
    arg_parser.add_argument('urls', metavar='URL',
                            type=str, nargs='+',
                            help='web page url')

    args = arg_parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    logging.info('WebPageArchiver started\n')
    archived = 0
    for url in args.urls:
        archived += archive(url, args.metadata)
    if archived == len(args.urls):
        logging.info(f'Archived pages: {archived}/{len(args.urls)}')
    else:
        logging.warning(f'Archived pages: {archived}/{len(args.urls)}')
    logging.info('WebPageArchiver finished')
