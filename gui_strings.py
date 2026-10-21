"""Czech texts for the GUI. The English text is the key; missing keys simply stay English.
To add a language: add another dict and extend tr()."""
CS = {
    "Finds the best moments in your stream recordings. Free and runs on your PC.": "Najde nejlepší momenty ve tvých záznamech streamu. Zdarma a běží na tvém PC.",
    "Source & output": "Zdroj a výstup", "Clip selection": "Výběr klipů", "Detection signals": "Signály detekce",
    "AI suggestions (optional)": "AI návrhy (nepovinné)", "Secret word": "Tajné slovo", "Trigger words": "Trigger slova",
    "Recording (video file)": "Záznam (video soubor)", "...or Twitch VOD link": "...nebo odkaz na Twitch VOD", "Save clips to": "Kam uložit klipy",
    "Browse": "Vybrat", "Max clips": "Max. počet klipů", "Strictness": "Přísnost výběru", "Seconds before peak": "Sekund před vrcholem",
    "Seconds after peak": "Sekund po vrcholu", "Min. gap between clips": "Min. odstup klipů", "Cut video clips (off = timestamps only)": "Vystřihnout klipy (vypnuto = jen časy)",
    "Loudness detection (shouting, laughing)": "Detekce hlasitosti (křik, smích)", "Minimum loudness jump": "Minimální skok hlasitosti",
    "Speech detection (trigger words)": "Detekce řeči (trigger slova)", "Transcription quality": "Kvalita přepisu", "Speech language": "Jazyk řeči",
    "Processor": "Procesor", "Rate clips, suggest hashtags and memes": "Ohodnotit klipy, navrhnout hashtagy a memy", "Ollama model name": "Název modelu Ollama",
    "Minimum funny rating": "Minimální hodnocení vtipnosti", "Seconds to look back": "Kolik sekund zpět vzít",
    "Save": "Uložit", "Open folder": "Otevřít složku", "▶  Start analysis": "▶  Spustit analýzu", "■  Stop": "■  Stop", "Ready": "Připraveno",
    "↺ Reset all": "↺ Obnovit vše", "Reset to default": "Obnovit výchozí hodnotu", "Cancelled.": "Zrušeno.", "Finished. See the Results tab.": "Hotovo. Podívej se do záložky Results.",
    "Reset": "Obnovit", "Reset all settings to their defaults? Your keyword lists, file paths, secret word and AI model name stay as they are.": "Obnovit všechna nastavení na výchozí? Seznamy slov, cesty, tajné slovo a název AI modelu zůstanou.",
    "No results found.": "Žádné výsledky.", "No clips found. Try a lower Strictness or Minimum loudness jump.": "Žádné klipy. Zkus nižší přísnost nebo nižší skok hlasitosti.",
    "Why picked:": "Proč vybráno:", "AI rating:": "Hodnocení AI:", "Funniest moment:": "Nejvtipnější moment:", "Evidence:": "Citát:",
    "⚠ not found in the transcript - the AI may be wrong": "⚠ v přepisu nenalezeno - AI se může mýlit", "Title:": "Název:", "Hashtags:": "Hashtagy:",
    "Measurement finished. See the Log.": "Měření dokončeno. Podívej se do záložky Log.",
    "Game being played": "Hraná hra", "Always add these hashtags": "Vždy přidat tyto hashtagy",
    "The game in this recording, e.g. Project Zomboid. The AI adds hashtags for the game, its genre and its community.": "Hra v tomto záznamu, např. Project Zomboid. AI přidá hashtagy pro hru, její žánr a komunitu.",
    "Your own hashtags for every clip, e.g. #yourchannel. Separate with spaces. They are added at the end of the list.": "Tvoje vlastní hashtagy ke každému klipu, např. #tvujkanal. Odděl je mezerou. Přidají se na konec seznamu.",
    "Clips": "Klipy", "Clips window": "Okno s klipy", "▶  Play clip": "▶  Přehrát klip", "Copy all posts": "Kopírovat všechny příspěvky",
    "Hashtags are ordered broad → niche (an AI estimate). You can edit any text, then copy. All texts are also saved in posts.txt.": "Hashtagy jsou řazené od širokých k nišovým (odhad AI). Texty můžeš upravit a pak zkopírovat. Všechny texty jsou i v posts.txt.",
    "Description": "Popisek", "Hashtags": "Hashtagy", "hashtags": "hashtagů", "Copy top 5": "Kopírovat top 5", "Copy top 10": "Kopírovat top 10",
    "Copy all tags": "Kopírovat všechny tagy", "Copy full post": "Kopírovat celý příspěvek", "Copied ✓": "Zkopírováno ✓",
    "Show transcript": "Zobrazit přepis", "Hide transcript": "Skrýt přepis", "(no preview)": "(bez náhledu)", "MARKER": "ZNAČKA",
    "No clip file": "Soubor klipu chybí", "This clip was not cut (the option 'Cut video clips' was off).": "Tento klip nebyl vystřižen (volba 'Cut video clips' byla vypnutá).",
    "No results yet. Run an analysis first.": "Zatím žádné výsledky. Nejdřív spusť analýzu.",
    "+  Add finished clip": "+  Přidat hotový klip", "FINISHED": "HOTOVÝ KLIP", "General": "Obecné", "Title": "Název", "recommended": "doporučeno",
    "Busy": "Probíhá analýza", "An analysis is already running. Wait for it to finish or press Stop.": "Analýza už běží. Počkej na dokončení nebo dej Stop.",
    "Finished clips analyzed. See the Clips window.": "Hotové klipy analyzovány. Podívej se do okna s klipy.",
    "No clips yet. Click '+ Add finished clip' to analyze a clip you already have (for example exported from DaVinci Resolve), or run a stream analysis in the main window.": "Zatím tu nejsou žádné klipy. Klikni na '+ Přidat hotový klip' a analyzuj klip, který už máš (třeba exportovaný z DaVinci Resolve), nebo spusť analýzu streamu v hlavním okně.",
    "Analysis": "Analýza", "Reload": "Znovu načíst", "Refresh": "Obnovit",
    "Ollama is not running or not installed. Start it, then press Refresh.": "Ollama neběží nebo není nainstalovaná. Spusť ji a stiskni Obnovit.",
    "No models installed yet. In a terminal run: ollama pull <model name>": "Zatím není nainstalovaný žádný model. V terminálu spusť: ollama pull <název modelu>",
    "Installed:": "Nainstalováno:", "GPU memory": "Paměť grafiky",
    "* = probably too large for your GPU memory (much slower).": "* = pravděpodobně větší než paměť tvé grafiky (mnohem pomalejší).",
    "Any model you installed with 'ollama pull' (see 'ollama list'). All Ollama models are free to download; the limit is your GPU memory - bigger models understand humor better but are slower, and models larger than your GPU memory are much slower.": "Libovolný model nainstalovaný přes 'ollama pull' (viz 'ollama list'). Všechny modely Ollama se stahují zdarma; limitem je paměť grafiky - větší modely chápou humor líp, ale jsou pomalejší, a modely větší než paměť grafiky jsou mnohem pomalejší.",
    "(no preview - install Pillow: py -m pip install pillow)": "(bez náhledu - nainstaluj Pillow: py -m pip install pillow)",
    "☆ Favorite": "☆ Oblíbené", "★ Favorite": "★ Oblíbené", "Delete": "Smazat", "Favorites only": "Jen oblíbené", "Delete clip": "Smazat klip",
    "Remove this clip?": "Odebrat tento klip?",
    "Yes = delete the file from disk and remove it from the list\nNo = only remove it from the list\nCancel = do nothing": "Ano = smazat soubor z disku a odebrat ze seznamu\nNe = jen odebrat ze seznamu\nZrušit = nedělat nic",
    "No favorites yet. Click ☆ Favorite on a clip.": "Zatím žádné oblíbené. Klikni u klipu na ☆ Oblíbené.",
    "Audio track for analysis": "Zvuková stopa pro analýzu",
    "Recordings from OBS can contain several audio tracks. Track 1 is usually everything mixed (game, music and voice). If your microphone is on its own track (for example track 2), choose it: loudness and speech are then measured from your voice only, which usually gives much better clips. A Twitch VOD normally has only one track.": "Záznamy z OBS mohou mít víc zvukových stop. Stopa 1 bývá všechno smíchané (hra, hudba a hlas). Pokud máš mikrofon na vlastní stopě (třeba 2), vyber ji: hlasitost i řeč se pak měří jen z tvého hlasu, což obvykle dá mnohem lepší klipy. Twitch VOD má obvykle jen jednu stopu.",
    "Remove from the list (the files stay on disk)": "Odebrat ze seznamu (soubory zůstanou na disku)",
    "Which game?": "Jaká hra?", "OK": "OK", "Cancel": "Zrušit",
    "Which game are these clips from? It is used for the game hashtags. Leave it empty if you do not want game hashtags.": "Z jaké hry jsou tyto klipy? Použije se pro hashtagy ke hře. Nech prázdné, když hashtagy ke hře nechceš.",
    "Hashtag pool size": "Velikost seznamu hashtagů",
    "How many hashtags the AI collects in the General tab - a big list to pick from. TikTok, YouTube Shorts and Reels use far fewer (more hashtags do not add reach there).": "Kolik hashtagů AI nasbírá v záložce General - velký seznam k výběru. TikTok, YouTube Shorts a Reels používají mnohem míň (víc hashtagů tam dosah nezvyšuje).",
    "50 gives you a big list to choose from in the General tab. The platform tabs use only the recommended number anyway.": "50 ti dá velký seznam k výběru v záložce General. Záložky platforem stejně používají jen doporučený počet.",
    "Measure my loudness": "Změřit mou hlasitost", "Measure": "Změřit", "Use suggestion": "Použít návrh",
    "Enjoying the app? Support it on Ko-fi": "Líbí se ti program? Podpoř ho na Ko-fi",
    "Analyzes the loudness of the selected recording and shows how loud your normal voice is compared with your loudest moments, so you can match the setting to your microphone. Tip: pick a recording that contains some of your yelps. Takes a minute or two for a long video.":
        "Rozebere hlasitost vybraného záznamu a ukáže, jak hlasitý je tvůj běžný hlas oproti nejhlasitějším momentům, abys nastavení přizpůsobil svému mikrofonu. Tip: vyber záznam, kde jsou nějaké tvoje výkřiky. U dlouhého videa to trvá minutu nebo dvě.",
    "Typical level {typical} dB. About 90% of the time you stay within +{p90} dB of that; your loudest 1% goes above +{p99} dB (loudest +{max} dB). Suggested minimum jump: {suggest} dB. The log lists your loudest moments - listen to them to check it was you and not the game.":
        "Typická hlasitost {typical} dB. Zhruba 90 % času se držíš do +{p90} dB od ní; nejhlasitější 1 % jde nad +{p99} dB (špička +{max} dB). Navržený minimální skok: {suggest} dB. V logu jsou tvoje nejhlasitější momenty - poslechni si je a ověř, že jsi to byl ty a ne hra.",
    "Meme/GIF ideas:": "Nápady na meme/GIF:", "Transcript:": "Přepis:", "▶ open clip": "▶ otevřít klip",
    # tooltips
    "A recording of your stream (.mp4, .mkv, ...).": "Záznam tvého streamu (.mp4, .mkv, ...).",
    "Paste a VOD link and it will be downloaded first. Only use content you have the rights to.": "Vlož odkaz na VOD a nejdřív se stáhne. Používej jen obsah, na který máš práva.",
    "Folder where the clips and clips.txt are saved.": "Složka, kam se uloží klipy, clips.txt a přepis.",
    "The N best moments are kept.": "Ponechá se N nejlepších momentů.",
    "Lower = more clips (also weaker ones). Higher = only the most striking moments.": "Nižší = víc klipů (i slabších). Vyšší = jen ty nejvýraznější.",
    "How much lead-up is included in each clip.": "Kolik děje před momentem se vezme do klipu.", "How much is included after the moment.": "Kolik děje po momentu.",
    "Prevents several clips of the same moment.": "Zabrání více klipům stejného momentu.",
    "A moment counts as a loud spike only if it is at least this many dB louder than your normal level over the last 3 minutes. Roughly: +6 dB = clearly louder, +10 dB = sounds about twice as loud, +15 dB or more = shouting. Lower = more sensitive. After a run the log shows the loudest spike found, which helps you tune this.":
        "Moment se počítá jako hlasitý, jen když je aspoň o tolik dB hlasitější než tvoje běžná hlasitost za poslední 3 minuty. Zhruba: +6 dB = znatelně hlasitější, +10 dB = zní dvakrát hlasitěji, +15 dB a víc = křik. Nižší = citlivější. Log po běhu ukáže nejhlasitější špičku, což pomůže s laděním.",
    "The model is the 'brain' that turns speech into text. Bigger = more accurate but slower and needs more memory (Accurate needs about 5 GB of GPU memory).":
        "Model je 'mozek', který mění řeč na text. Větší = přesnější, ale pomalejší a potřebuje víc paměti (Accurate asi 5 GB paměti grafiky).",
    "The language you mostly speak. 'Mixed' tries to detect the language of every sentence - experimental, switch back if the text looks odd.":
        "Jazyk, kterým hlavně mluvíš. 'Mixed' hádá jazyk u každé věty - experimentální, když text vychází divně, vrať se zpět.",
    "GPU (NVIDIA) is much faster. If the GPU fails or you have none, choose CPU - slower but works everywhere.": "GPU (NVIDIA) je mnohem rychlejší. Když GPU selže nebo ji nemáš, zvol CPU - pomalejší, ale funguje všude.",
    "Say this phrase right after something great happens. A clip is ALWAYS created, covering the seconds before you said it. Leave empty to disable.":
        "Řekni tuto frázi hned po skvělém momentu. Klip vznikne VŽDY a pokryje vteřiny před vyslovením. Prázdné = vypnuto.",
    "How much footage before the phrase is saved.": "Kolik záznamu před frází se uloží.",
    "When you say one of these, that moment gets a bonus. One word or phrase per line. 'Strong' words give a much bigger bonus. Click Save to keep changes.":
        "Když řekneš některé z nich, moment dostane bonus. Jedno slovo nebo fráze na řádek. Silná slova dají mnohem větší bonus. Změny ulož tlačítkem Uložit.",
    "Uses a free AI that runs on your PC (Ollama, ollama.com) to rate how funny each candidate is, explain why, and suggest a title, hashtags and meme/GIF ideas. Install Ollama, then run once in a terminal: ollama pull <model name>. Nothing is sent online.":
        "Využívá zdarma AI na tvém PC (Ollama, ollama.com): ohodnotí vtipnost kandidátů, zdůvodní ji a navrhne název, hashtagy a nápady na meme/GIF. Nainstaluj Ollama a jednou v terminálu spusť: ollama pull <název modelu>. Nic se neposílá online.",
    "Any model you installed with 'ollama pull' (see 'ollama list'). Bigger models understand humor better but are slower.": "Libovolný model nainstalovaný přes 'ollama pull' (viz 'ollama list'). Větší modely chápou humor líp, ale jsou pomalejší.",
    "Only clips the AI rates at least this high (out of 10) are kept. With AI on, a wider pool of candidates is checked than normal.": "Ponechají se jen klipy s hodnocením AI aspoň tolik (z 10). Se zapnutou AI se kontroluje širší výběr kandidátů.",
    # reasons for defaults
    "15 gives you enough clips to choose from without drowning in them.": "15 dá dost klipů na výběr a nezahltí tě.",
    "3.0 means a moment needs a clear signal (about +15 dB louder than usual, or trigger words). Lower values mostly add noise.": "3.0 znamená, že moment potřebuje jasný signál (asi +15 dB nad normál nebo trigger slova). Nižší hodnoty většinou jen přidají šum.",
    "20 s usually covers the build-up to a reaction.": "20 s obvykle pokryje rozjezd k reakci.", "10 s covers the reaction itself; longer clips tend to drag.": "10 s pokryje samotnou reakci; delší klipy se táhnou.",
    "60 s avoids picking the same moment twice.": "60 s zabrání výběru stejného momentu dvakrát.",
    "45 s is long enough to include whatever just happened before you said the phrase.": "45 s stačí na to, co se stalo těsně před vyslovením fráze.",
    "6 dB is where a sound is clearly louder than normal speech level; lower picks up ordinary variation.": "6 dB je hranice, kdy je zvuk jasně hlasitější než běžná řeč; nižší hodnota chytá obyčejné kolísání.",
    "5/10 keeps clips the AI finds at least moderately funny.": "5/10 ponechá klipy, které AI považuje aspoň za středně vtipné.",
}
_CS = {" ".join(k.split()): v for k, v in CS.items()}


def tr(text, lang):
    """Translate a text (paragraph by paragraph). English is returned unchanged."""
    if lang != "cs" or not isinstance(text, str):
        return text
    out = []
    for p in text.split("\n\n"):
        out.append("Výchozí: " + p[9:] if p.startswith("Default: ") else _CS.get(" ".join(p.split()), p))
    return "\n\n".join(out)
