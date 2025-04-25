import hashlib
import mimetypes
import os
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


class StaticSiteCloner:
    def __init__(self, target_url):
        self.target_url = target_url
        self.base_domain = urlparse(target_url).netloc
        self.assets_dir = "static"
        self.downloaded_resources = {}
        os.makedirs(self.assets_dir, exist_ok=True)

    def _process_url(self, url):
        """统一资源路径处理"""
        if url.startswith("//"):
            return f"https:{url}"
        if not url.startswith(("http", "https")):
            return urljoin(self.target_url, url)
        return url

    def _save_resource(self, content, extension):
        """带哈希值的文件名保存"""
        file_hash = hashlib.md5(content).hexdigest()[:8]
        filename = f"{file_hash}.{extension}"
        with open(os.path.join(self.assets_dir, filename), "wb") as f:
            f.write(content)
        return filename

    def clone_page(self):
        # 下载主页面
        response = requests.get(self.target_url)
        soup = BeautifulSoup(response.text, "html.parser")

        # 处理所有资源标签
        for tag in soup.find_all(["img", "script", "link"]):
            if tag.name == "img" and tag.get("src"):
                attr = "src"
                try:
                    res = requests.get(self._process_url(tag[attr]), timeout=10)
                    content_type = res.headers["Content-Type"].split(";")[0]
                    if content_type.startswith("image/"):
                        extension = content_type.split("/")[1]
                        # 对于webp等格式，直接从URL获取扩展名作为后备
                        if not extension or extension == "octet-stream":
                            path = urlparse(tag[attr]).path
                            extension = path.split(".")[-1] if "." in path else "bin"
                        filename = self._save_resource(res.content, extension)
                        tag[attr] = f"/{self.assets_dir}/{filename}"
                except Exception as e:
                    print(f"Failed to download image {tag[attr]}: {str(e)}")
                continue
            elif tag.name == "script" and tag.get("src"):
                attr = "src"
            elif tag.name == "link" and tag.get("href"):
                attr = "href"
                # 处理link标签中的图标资源
                if tag.get("rel") and "icon" in tag["rel"]:
                    try:
                        res = requests.get(self._process_url(tag[attr]), timeout=10)
                        content_type = res.headers["Content-Type"].split(";")[0]
                        if content_type.startswith("image/"):
                            extension = content_type.split("/")[1]
                            filename = self._save_resource(res.content, extension)
                            tag[attr] = f"/{self.assets_dir}/{filename}"
                    except Exception as e:
                        print(f"Failed to download icon {tag[attr]}: {str(e)}")
                    continue
            else:
                continue

            original_url = self._process_url(tag[attr])
            if urlparse(original_url).netloc != self.base_domain:
                continue  # 跳过外部资源

            try:
                res = requests.get(original_url, timeout=10)
                content_type = res.headers["Content-Type"].split(";")[0]
                extension = mimetypes.guess_extension(content_type)

                # 如果无法从Content-Type确定扩展名，尝试从URL中获取
                if not extension:
                    path = urlparse(original_url).path
                    extension = path.split(".")[-1] if "." in path else "bin"
                else:
                    extension = extension.lstrip(".")

                filename = self._save_resource(res.content, extension)
                tag[attr] = f"/{self.assets_dir}/{filename}"
            except Exception as e:
                print(f"Failed to download {original_url}: {str(e)}")

        # 保存处理后的HTML
        with open("index.html", "w", encoding="utf-8") as f:
            f.write(str(soup))
        print("克隆完成！现在可以部署到Vercel")


if __name__ == "__main__":
    cloner = StaticSiteCloner("https://news.nilh2a2.dev/")
    cloner.clone_page()
