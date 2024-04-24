import os
import sys
import time
import json
import shutil
import datetime
from typing import List, Tuple

DEFAULT_LOCALE = "cs"
LOCALE_DATE_FMTS = {
    "en": "%Y-%m-%d",
    "cs": "%d.%m.%Y",
}

BUILD_PATH="build"
CONTENTS_FILE="contents.json"
ARTICLES_PATH="articles"
ARTICLE_SUMMARY_TEMPL_FILE="summary-template.html"
ARTICLE_FULL_TEMPL_FILE="full-template.html"
SUPPLEMENTARY_PATH="suppls"
SUPPLEMENTARY_SUMMARY_TEMPL_FILE="summary-template.html"

def refresh_folder(folder_path: str) -> str:
    if os.path.exists(folder_path):
        print(f"INFO: deleting old build")
        shutil.rmtree(folder_path)

    print(f"INFO: scaffolding new build")
    os.makedirs(folder_path)
    os.makedirs(os.path.join(folder_path, ARTICLES_PATH))
    os.makedirs(os.path.join(folder_path, SUPPLEMENTARY_PATH))

def fmt_timestamp(stamp: int, locale: str) -> str:
    dt = datetime.datetime.fromtimestamp(stamp)
    return dt.strftime(LOCALE_DATE_FMTS[locale])

def fmt_duration(secs: int):
    hs = secs // 3600
    ms = (secs % 3600) // 60
    ss = secs % 60

    out = ""
    if hs > 0: out += f"{int(hs)} h, "
    if ms > 0: out += f"{int(ms)} m, "
    if ss > 0: out += f"{int(ss)} s"

    return out.strip()


def apply_vars(s: str, props = {}):
    locale = props.get("locale") or DEFAULT_LOCALE
    
    var_map = {
        "%CURRENT-DATE%": lambda: fmt_timestamp(int(datetime.datetime.now().timestamp()), locale),
        "%UPDATED-AT%":   lambda: fmt_timestamp(int(props["updated-at"]), locale),
        "%WRITTEN-AT%":   lambda: fmt_timestamp(int(props["written-at"]), locale),
        "%TIME-TO-READ%": lambda: fmt_duration(len(props["content"].split())/2.7),
        "%TITLE%":        lambda: props["title"],
        "%PATH%":         lambda: props["path"],
        "%CONTENT%":      lambda: props["content"],
        "%AUTHOR%":       lambda: props["author"],
    }

    for var in var_map.keys():
        if var in s:
            s = s.replace(var, var_map[var]())
    
    return s


def get_contents():
    print(f"INFO: fetching metadata from {CONTENTS_FILE}")
    with open(CONTENTS_FILE, 'r') as f:
        content = json.load(f)
        
        arts = content["articles"]
        sups = content["supplements"]
        
        for i in range(len(arts)):
            arts[i]["path"] = "/articles/" + arts[i]["location"]
        for i in range(len(sups)):
            sups[i]["path"] = "/suppls/" + sups[i]["location"]
        
        return (arts, sups) 


def gen_article_summaries(articles):
    print(f"INFO: generating article summaries")
    with open(os.path.join(ARTICLES_PATH, ARTICLE_SUMMARY_TEMPL_FILE), "r") as f:
        template = f.read()

    return "\n".join([apply_vars(template, props) for props in articles])


def gen_suppl_summaries(suppls):
    print(f"INFO: generating supplementary summaries")
    with open(os.path.join(SUPPLEMENTARY_PATH, SUPPLEMENTARY_SUMMARY_TEMPL_FILE), "r") as f:
        template = f.read()

    return "\n".join([apply_vars(template, props) for props in suppls])


def port_static():
    shutil.copytree("styles",  os.path.join(BUILD_PATH, "styles"))
    shutil.copytree("scripts", os.path.join(BUILD_PATH, "scripts"))
    shutil.copytree("fonts",   os.path.join(BUILD_PATH, "fonts"))
    shutil.copytree("media",   os.path.join(BUILD_PATH, "media"))

def port_index(art_sum: str, supp_sum: str):
    index_file_og = open("index.html", "r")
    index_file_cp = open(os.path.join(BUILD_PATH,"index.html"), "w+")
    index_file_cp.write(apply_vars(index_file_og.read() \
        .replace("%ARTICLE-SUMMARIES%", art_sum) \
        .replace("%SUPPLEMENTARY-SUMMARIES%", supp_sum))
    )
    
    index_file_og.close()
    index_file_cp.close()


def port_articles(articles) -> None:
    print(f"INFO: porting articles")
    
    with open(os.path.join(ARTICLES_PATH, ARTICLE_FULL_TEMPL_FILE), "r") as f:
        template = f.read()

    for i in range(len(articles)):
        with open(os.path.join(ARTICLES_PATH, articles[i]["location"], "index.html"), "r") as f:
            print(f"          + {articles[i]['location']}")
            articles[i]["content"] = f.read()
            article_file_content = apply_vars(template, articles[i])
            os.makedirs(os.path.join(BUILD_PATH, "articles", articles[i]["location"]))
            with open(os.path.join(BUILD_PATH,"articles", articles[i]["location"], "index.html"), "w+") as dest:
                dest.write(article_file_content)
            
            for m in os.listdir(os.path.join(ARTICLES_PATH, articles[i]["location"], "media")):
                shutil.copy2(os.path.join(ARTICLES_PATH, articles[i]["location"], "media", m), os.path.join(BUILD_PATH, "media"))
                

def port_supps(supps) -> None:
    print(f"INFO: porting supplementaries")
    
    for s in supps:
        print(f"          + {s['location']}")
        shutil.copytree(os.path.join(SUPPLEMENTARY_PATH, s["location"]), os.path.join(BUILD_PATH, "suppls", s["location"]))

def port_startpage():
    print(f"INFO: porting startpage")
    shutil.copytree("startpage/", os.path.join(BUILD_PATH, "startpage"))

def main(args: List[str]) -> int:
    start_time = time.time()
    
    # clean up
    refresh_folder(BUILD_PATH)
    
    # generata all metadata
    (arts, supps) = get_contents()
    
    # firstly port over the static stuff
    port_static()
    
    # then the index
    port_index(gen_article_summaries(arts), gen_suppl_summaries(supps))

    # then the articles
    port_articles(arts)
    
    # then the supplementaries    
    port_supps(supps)
    
    # finally the startpage
    port_startpage()
    
    delta = time.time() - start_time
    print(f"INFO: built in {delta:.3f}s")

    return 0


if __name__ == "__main__":
	sys.exit(main(sys.argv))
 