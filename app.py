import os
import psycopg2
import streamlit as st
import base64
import warnings
import pandas as pd

# 1. POSTAVKE STRANICE
st.set_page_config(page_title="Katastar Arhiva - Pregled", layout="wide")
warnings.filterwarnings("ignore", category=UserWarning)

# ---  BRISANJE GORNJE TRAKE I ZAŠTITA SLIKA ---
st.markdown("""
    <style>
    /* Trajno i neprobojno gasi cijelu gornju traku i Fork gumb na svim uređajima */
    [data-testid="stHeader"], header, [data-testid="stSidebar"] { display: none !important; height: 0px !important; }
    .block-container { padding-top: 1.5rem !important; }
    img { -webkit-touch-callout: none; -webkit-user-select: none; user-select: none; }
    div[data-testid='stImage'] img { pointer-events: none !important; }
    
    /* Responzivne prilagodbe za mobilne ekrane */
    @media (max-width: 767px) {
        h1 { font-size: 1.3rem !important; line-height: 1.2 !important; }
        h2, h3, .stSubheader { font-size: 1.05rem !important; }
        .block-container { padding-top: 1rem !important; }
    }
    </style>
""", unsafe_allow_html=True)


# ---  ZAŠTITA ZA ULAZ ---
if "autentificiran" not in st.session_state:
    st.session_state["autentificiran"] = False

if not st.session_state["autentificiran"]:
    st.subheader("🔐 Privatna Obiteljska Arhiva")
    u_korisnik = st.text_input("Korisnicko ime:")
    u_lozinka = st.text_input("Lozinka:", type="password")
    if st.button("Pristupi arhivi"):
        if u_korisnik == st.secrets["credentials"]["username"] and u_lozinka == st.secrets["credentials"]["password"]:
            st.session_state["autentificiran"] = True
            st.rerun()
        else: st.error("❌ Nevazeće lozinke.")
    st.stop()

    # Postavljanje zadanih vrijednosti u memoriju aplikacije na samom početku
if "odabrana_zona" not in st.session_state: st.session_state["odabrana_zona"] = "Sve zone"
if "odabrani_zk" not in st.session_state: st.session_state["odabrani_zk"] = "Svi ZK ulošci"
if "odabrana_vrsta_lista" not in st.session_state: st.session_state["odabrana_vrsta_lista"] = "Sve vrste lista"


# --- SPAJANJE NA BAZU S TIMEOUTOM ---
conn = psycopg2.connect(
    host=st.secrets["baza"]["host"], port=st.secrets["baza"]["port"],
    database=st.secrets["baza"]["database"], user=st.secrets["baza"]["user"],
    password=st.secrets["baza"]["password"], sslmode=st.secrets["baza"]["sslmode"],
    options="-c statement_timeout=5000"
)
cursor = conn.cursor()


# =========================================================================
# 🧹 MEHANIZAM ZA ULTRA-BRZO ČIŠĆENJE MEMORIJE PRI PROMJENI EKRANA
# =========================================================================
if "zadnji_odabir" not in st.session_state:
    st.session_state["zadnji_odabir"] = "🗺️ Pregled i pretraga čestica"

# Prisluškujemo promjenu na radijskim gumbima navigacije
if "navigacija_izbor" in st.session_state:
    trenutni_izbor = st.session_state["navigacija_izbor"]
    
    # Ako je korisnik kliknuo na neki drugi odjeljak (npr. Matične knjige)
    if trenutni_izbor != st.session_state["zadnji_odabir"]:
        # Resetiramo odabir čestice natrag na "SVE" kako bismo ugasili pojedinačni prikaz i b64 upite
        if "odabrana_c_kljuc" in st.session_state:
            st.session_state["odabrana_c_kljuc"] = "SVE"
        
        # Spremamo novo stanje navigacije (BEZ st.rerun(), dopuštamo aplikaciji da normalno promijeni ekran)
        st.session_state["zadnji_odabir"] = trenutni_izbor

# =========================================================================
# 🏛️ UNUTARNJI BOČNI IZBORNIK PREKO ST.COLUMNS (ZAMJENA ZA SIDEBAR)
# =========================================================================
popis_opcija = ["🗺️ Pregled i pretraga čestica", "📋 Posjedovni listovi", "📜 Matične knjige", "📂 Dokumenti", "👥 Odabir čestica", "⚖️ Upravljanje Diobom"]

glavni_col1, glavni_col2 = st.columns([1, 4])

with glavni_col1:
    st.markdown("### 🧭 Navigacija")
    je_admin = st.query_params.get("admin") == "da"
    prikazane_opcije = popis_opcija if je_admin else popis_opcija[:-1]
    izbor = st.radio("Odaberite odjeljak:", prikazane_opcije, label_visibility="collapsed", key="navigacija_izbor")
    
    st.markdown("[🌍 Pozicija čestice na karti](https://oss.uredjenazemlja.hr/map)")
    st.write("---")
    
          # --- BRZI FILTERI UNUTAR LIJEVOG STUPCA ---
    if izbor == "🗺️ Pregled i pretraga čestica":
        
        trenutna_c = st.session_state.get("odabrana_c_kljuc", "SVE")
        
        if trenutna_c == "SVE":      
            st.markdown("### 🔍 Napredno filtriranje")

            
            # Zone
            cursor.execute("SELECT DISTINCT zona FROM cestice WHERE zona IS NOT NULL AND zona != '' ORDER BY zona")
            sve_zone = ["Sve zone"] + [r for r, in cursor.fetchall()]
            odabrana_zona = st.pills("Zona:", sve_zone, default="Sve zone", key="zona_filter")
            

            with st.popover("📖 Legenda - zone", use_container_width=True):
                st.markdown("""
            **Službena značenja oznaka (Grad Obrovac):**
            
            * **M4** – **Mješovita namjena:** Građevinska zona unutar naselja predviđena za stanovanje i prateće obiteljske/gospodarske sadržaje
            * **OZ-1** – **Ostalo zemljište:** Krš i neplodno tlo. Dozvoljena samo manja spremišta za alat i kućice za čuvanje maslinika/vinograda
            * **ŠO-1** – **Zemljište namijenjeno šumi:** Šumsko tlo. Dozvoljena je gradnja šumske infrastrukture (planinarski/lovački domovi)
            * **VZP-1** – **Vrijedno poljoprivredno zemljište:** Visokokvalitetno poljoprivredno tlo izvan obalnog pojasa; nije građevinska zona 
            * **ZOP-1000** – **Zaštićeni obalni pojas:** Područje unutar 1000m od mora pod strogom državnom zaštitom i ograničenjima.
            * **T2** – **Turistička namjena:** Područje predviđeno isključivo za hotele i turistička naselja.
            """)
                
            
            # ZK Ulošci
            cursor.execute("SELECT DISTINCT zk_ulozak FROM cestice WHERE zk_ulozak IS NOT NULL ORDER BY zk_ulozak")
            svi_zk = ["Svi ZK ulošci"] + [str(r) for r, in cursor.fetchall()]
            odabrani_zk = st.pills("ZK uložak:", svi_zk, default="Svi ZK ulošci", key="zk_filter")
            
            # Vrste listova
            cursor.execute("""
                SELECT DISTINCT pd.vrsta_lista FROM povijest_dokumenata pd
                WHERE pd.vrsta_lista IN ('Vlasnički list', 'Posjedovni list')
                  AND pd.id_cestice NOT IN (SELECT id FROM cestice WHERE id IN (999999, 777777))
                ORDER BY pd.vrsta_lista
            """)
            sve_vrste_lista = ["Sve vrste lista"] + [r for r, in cursor.fetchall()]
            odabrana_vrsta_lista = st.pills("Vrsta lista:", sve_vrste_lista, default="Sve vrste lista", key="lista_filter")
        else:
            st.caption("🔍 _Napredni filteri dostupni su u pregledu svih čestica._")
            odabrana_zona = st.session_state.get("zona_filter", "Sve zone")
            odabrani_zk = st.session_state.get("zk_filter", "Svi ZK ulošci")
            odabrana_vrsta_lista = st.session_state.get("lista_filter", "Sve vrste lista")
    else:
        # Sigurnosne zadane vrijednosti za ostale ekrane (sprječava preostale greške)
        odabrana_zona = "Sve zone"
        odabrani_zk = "Svi ZK ulošci"
        odabrana_vrsta_lista = "Sve vrste lista"
        

    st.write("---")

# =========================================================================
# 🚀 DESNI DIO: LOGIKA PRIKAZA EKRANA OVISNO O ODABIRU
# =========================================================================
with glavni_col2:
    if izbor == "🗺️ Pregled i pretraga čestica":    
        st.title("🗺️ Obiteljska Arhiva Katastra")
        if "uploader_kljuc" not in st.session_state: st.session_state["uploader_kljuc"] = 0
        up_doc = st.file_uploader("Učitaj novi dokument:", type=["png", "jpg", "jpeg", "pdf", "xlsx"], key=f"up_{st.session_state['uploader_kljuc']}")

        if up_doc is not None:
            try:
                b64 = base64.b64encode(up_doc.read()).decode('utf-8')
                cursor.execute("INSERT INTO povijest_dokumenata (id_cestice, vrsta_lista, broj_lista_korisnika, datoteka) VALUES (NULL, 'Poslani dokument', 'Online', %s)", (f"{up_doc.name}|||{b64}",))
                conn.commit()
                st.success("✅ Spremljeno u bazu!")    
                st.session_state["uploader_kljuc"] += 1
                st.rerun()
            except Exception as e: st.error(f"Greška: {e}")

        st.write("---")
        col_f1, col_f2 = st.columns(2)
        
        cursor.execute("SELECT id, naziv_podrucja FROM podrucja")
        p_dict = {naziv: id for id, naziv in cursor.fetchall()}
        with col_f1: odabrano_p = st.selectbox("Odaberi područje:", ["Sva područja"] + list(p_dict.keys()))

            
        upit_za_cestice = "SELECT c.id, c.broj_cestice FROM cestice c WHERE c.id NOT IN (999999, 777777)"
        parametri_c = []
        
        
        if odabrano_p != "Sva područja":
            upit_za_cestice += " AND c.id_podrucja = %s"
            parametri_c.append(p_dict[odabrano_p])
            
        if odabrana_zona != "Sve zone":
            upit_za_cestice += " AND c.zona = %s"
            parametri_c.append(odabrana_zona)
            
        if odabrani_zk != "Svi ZK ulošci":
            upit_za_cestice += " AND c.zk_ulozak::text = %s"
            parametri_c.append(odabrani_zk)
            
        if odabrana_vrsta_lista != "Sve vrste lista":
            upit_za_cestice += """ 
                AND EXISTS (
                    SELECT 1 FROM povijest_dokumenata pd 
                    WHERE pd.id_cestice = c.id 
                      AND pd.vrsta_lista = %s
                )
            """
            parametri_c.append(odabrana_vrsta_lista)

        upit_za_cestice += " ORDER BY c.broj_cestice"
        cursor.execute(upit_za_cestice, tuple(parametri_c))
        c_dict = {broj: id for id, broj in cursor.fetchall()}
        
        

        # Popis sadrži isključivo prave brojeve čestica iz baze
        opcije_cestica = list(c_dict.keys())

        with col_f2: 
            odabrana_c_izbor = st.selectbox(
                "Odaberi broj čestice:", 
                options=opcije_cestica,
                index=None,  # Početno NIŠTA nije odabrano (što znači da se prikazuje velika tablica)
                placeholder="Prikaži sve čestice..."  # Ovaj tekst se briše sam od sebe čim kliknete!
            )
            
        # Ako je korisnik odabrao česticu, koristimo nju, inače idemo na "SVE"
        odabrana_c = odabrana_c_izbor if odabrana_c_izbor is not None else "SVE"



        st.write("---")
        
        # 1. PROMIJENJENO: Uvjet provjerava čistu riječ "SVE" (sigurno za online rad)

        
        if odabrana_c != "SVE":
            cursor.execute("SELECT c.zk_ulozak, c.broj_zadnjeg_dnevnika, c.oznaka_zemljista, c.naziv_zemljista, c.napomena, c.povrsina, p.naziv_podrucja, c.katastarska_opcina, c.sifra, c.zona FROM cestice c JOIN podrucja p ON c.id_podrucja = p.id WHERE c.id = %s", (c_dict[odabrana_c],))
            zk, dn, oz, nz, nap, pov, lok, ko, sif, zon = cursor.fetchone()
            st.markdown(f"### 📍 Podaci za česticu: **{odabrana_c}** ({lok})")
            c1, c2, c3 = st.columns(3)
            c1.info(f"**📑 K.O.:** {ko}\n\n**🔢 ZK Uložak:** {zk}")
            c2.info(f"**🌿 Oznaka:** {oz}\n\n**🗺️ Naziv:** {nz}")
            c3.success(f"**🏷️ Zona:** `{zon if zon else '-'}`\n\n**📐 Površina:** {pov} m²")
            if nap: st.info(f"📝 Napomena: {nap}")
            
            st.write("---")
            st.markdown("### ⏳ Povijesna Arhiva Listova")
            cursor.execute("SELECT vrsta_lista, broj_lista_korisnika, starost_godina, upisani_vlasnik_posjednik, povijesna_napomena, id FROM povijest_dokumenata WHERE id_cestice = %s", (c_dict[odabrana_c],))
            

                        # Zadržan je vaš originalni raspored varijabli, gdje je 'dat' (sada ID) na kraju!
          


                     # Zamijenite vašu staru petlju s ovim popravljenim kodom:
            for v, br, st_g, vl, p_n, dat in cursor.fetchall():
                with st.expander(f"📄 {v} br. {br} ({st_g})"):
                    st.write(f"👤 {vl} | 💬 {p_n}")
                    
                    if st.button("👁️ Prikaži / Otvori dokument", key=f"btn_c_{dat}", use_container_width=True):
                        with st.spinner("⏳ Dohvaćam dokument iz arhive..."):
                            
                            # 1. ČISTI SQL TRIK: Izvlačimo dio iza '|||' i dekodiramo Base64 izravno na Postgres serveru!
                            # split_part razdvaja ime i b64 kod, a decode pretvara b64 u čiste binarne podatke (bytea)
                            cursor.execute("""
                                SELECT 
                                    split_part(datoteka, '|||', 1) as ime_datoteke,
                                    decode(split_part(datoteka, '|||', 2), 'base64') as binarni_podaci
                                FROM povijest_dokumenata 
                                WHERE id = %s
                            """, (dat,))
                            
                            rezultat = cursor.fetchone()
                            
                        # 2. Provjera i trenutni prikaz bez ikakvog mučenja memorije u Pythonu
                        if rezultat and rezultat[0] and rezultat[1]:
                            ime = rezultat[0]
                            # memoryview/bytes pretvara Postgres bytea izravno u čiste bajtove za download
                            binarni = bytes(rezultat[1])
                            
                            # A. Prikaz slika
                            if ime.lower().endswith(('.jpg', '.jpeg', '.png')):
                                st.html("<style>div[data-testid='stImage'] img {pointer-events: none !important;}</style>")
                                st.image(binarni, width='stretch')
                                
                            # B. Prikaz i otvaranje PDF-a
                            elif ime.lower().endswith('.pdf'):
                                st.success(f"✅ Dokument `{ime}` je uspješno učitan!")
                                st.download_button(
                                    "📥 Otvori / Preuzmi PDF", 
                                    binarni, 
                                    file_name=ime, 
                                    mime="application/pdf", 
                                    use_container_width=True
                                )
                        else:
                            st.error("❌ Greška: Datoteka ne postoji ili format nije ispravan.")

        # 2. KLJUČNI POPRAVAK: Umjesto čistog 'else:', stavljamo 'elif' koji provjerava čisti "SVE"
        # Ovo u potpunosti gasi tablicu na drugim ekranima i ubrzava navigaciju!

        
        elif odabrana_c == "SVE":
                   
            upit_tablica = """
                SELECT c.broj_cestice, c.zk_ulozak, c.katastarska_opcina, 
                       p.naziv_podrucja, c.naziv_zemljista, c.oznaka_zemljista, c.povrsina 
                FROM cestice c 
                JOIN podrucja p ON c.id_podrucja = p.id
                WHERE c.id NOT IN (999999, 777777)
                ORDER BY c.broj_cestice
            """
            parametri_t = []
            
            if odabrano_p != "Sva područja":
                upit_tablica += " AND c.id_podrucja = %s"
                parametri_t.append(p_dict[odabrano_p])
                
            if odabrana_zona != "Sve zone":
                upit_tablica += " AND c.zona = %s"
                parametri_t.append(odabrana_zona)
                
            if odabrani_zk != "Svi ZK ulošci":
                upit_tablica += " AND c.zk_ulozak::text = %s"
                parametri_t.append(odabrani_zk)
                
            if odabrana_vrsta_lista != "Sve vrste lista":
                upit_tablica += """ 
                    AND EXISTS (
                        SELECT 1 FROM povijest_dokumenata pd 
                        WHERE pd.id_cestice = c.id 
                          AND pd.vrsta_lista = %s
                    )
                """
                parametri_t.append(odabrana_vrsta_lista)
                
            df = pd.read_sql_query(upit_tablica, conn, params=parametri_t if parametri_t else None)
                        
            # ---  ZA ANALITIKU ---
            if not df.empty:
                # ZK uložak ostavljamo kao tekst (mora biti string) i pretvaramo NULL u prazan tekst
                df['zk_ulozak'] = df['zk_ulozak'].fillna('').astype(str)
                # Samo površinu pretvaramo u čisti broj za statistiku i računanje sume
                df['povrsina'] = pd.to_numeric(df['povrsina'], errors='coerce').fillna(0).astype(float)

            preimenovani_stupci = {
                "broj_cestice": "Broj čestice", 
                "zk_ulozak": "Broj ZK uloška", 
                "katastarska_opcina": "Katastarska općina", 
                "naziv_podrucja": "Područje", 
                "naziv_zemljista": "Naziv zemljišta",
                "oznaka_zemljista": "Oznaka zemljišta",
                "povrsina": "Površina (m²)"
            }
            df = df.rename(columns=preimenovani_stupci)
            
            # Prikaz tablice s otključanom analitikom na desni klik
            st.dataframe(df, width='stretch', hide_index=True)
        
            ukupna_povrsina = df['Površina (m²)'].sum() if not df.empty else 0
            st.write("")
            col_prazan1, col_prazan2, col_Desno = st.columns(3)
            with col_Desno:
                st.metric(
                    label=f"📐 Ukupna površina ({odabrano_p}):", 
                    value=f"{int(ukupna_povrsina):,}".replace(",", " ") + " m²"
                )
                      
            st.write("---")
    
            
        # =========================================================================
    # 📋 EKRAN 2: KATASTARSKI POSJEDOVNI LISTOVI
    # =========================================================================
    elif izbor == "📋 Posjedovni listovi":
        st.title("📋 Katastarski Posjedovni Listovi")
        
        # 1. Povlačimo ID i tekst, ali samo prvi dio (naziv datoteke) radi brzine
        cursor.execute("""
            SELECT id, split_part(datoteka, '|||', 1) 
            FROM povijest_dokumenata 
            WHERE vrsta_lista = 'Posjedovni list' 
              AND broj_lista_korisnika NOT ILIKE '%Ne postoji podatak o identifikaciji%'
            ORDER BY id DESC
        """)
        rezultati_baze = cursor.fetchall()

        if rezultati_baze:
            # Stvaramo čisti rječnik: ključ je naziv datoteke, vrijednost je ID u bazi
            pl_mape_id = {r[1]: r[0] for r in rezultati_baze if r[1] != ""}
            pl_imena = list(pl_mape_id.keys())
            
            odabrani_pl_ime = st.selectbox("📄 Odaberite posjedovni list:", [""] + pl_imena)
            
            if odabrani_pl_ime != "":
                odabrani_id = pl_mape_id[odabrani_pl_ime]
                
                with st.spinner("⏳ Dohvaćam dokument iz arhive..."):
                    # LAZY LOADING: Povlačimo cijeli Base64 string isključivo za odabrani ID
                    cursor.execute("SELECT datoteka FROM povijest_dokumenata WHERE id = %s", (odabrani_id,))
                    rezultat_doc = cursor.fetchone()
                
                if rezultat_doc and rezultat_doc[0] and "|||" in rezultat_doc[0]:
                    # Točno izvlačimo naziv i Base64 sadržaj iz baze podataka
                    naziv_datoteke, b64_sadrzaj = rezultat_doc[0].split("|||", 1)
                    binarni_podaci = base64.b64decode(b64_sadrzaj)
                    
                    st.write("---")
                    
                    # A. Ako je datoteka SLIKA (.jpg, .png)
                    if naziv_datoteke.lower().endswith(('.jpg', '.jpeg', '.png')):
                        st.html("<style>div[data-testid='stImage'] img {pointer-events: none !important;}</style>")
                        st.image(binarni_podaci, width='stretch')
                        st.download_button(label="📥 Preuzmi ovu sliku", data=binarni_podaci, file_name=naziv_datoteke, mime="image/jpeg", use_container_width=True, key=f"dl_pl_img_{odabrani_id}")
                    
                                        # B. Ako je datoteka PDF (Učitavanje prve stranice iz liste + gumb)
                    elif naziv_datoteke.lower().endswith('.pdf'):
                        try:
                            from pdf2image import convert_from_bytes
                            import io
                            
                            stranice = convert_from_bytes(binarni_podaci, dpi=130)
                            if stranice:
                                img_byte_arr = io.BytesIO()
                                # ISPRAVLJENO: Dodano [0] kako bismo spremili isključivo PRVU stranicu iz liste!
                                stranice[0].save(img_byte_arr, format='JPEG', quality=85)
                                cista_slika = img_byte_arr.getvalue()
                                
                                # Crtamo prvu stranicu PDF-a izravno na ekranu (Chrome radi 100%)
                                st.html("<style>div[data-testid='stImage'] img {pointer-events: none !important;}</style>")
                                st.image(cista_slika, width='stretch')
                                
                                # Gumb za preuzimanje kompletnog PDF-a
                                st.download_button(label="📥 Preuzmi cijeli PDF dokument", data=binarni_podaci, file_name=naziv_datoteke, mime="application/pdf", use_container_width=True, key=f"dl_pdf_ok_{odabrani_id}")
                        except Exception as e:
                            st.error(f"⚠️ Došlo je do greške pri iscrtavanju: {e}")
                            st.download_button("📥 Otvori / Preuzmi PDF", binarni_podaci, file_name=naziv_datoteke, mime="application/pdf", use_container_width=True, key=f"dl_pdf_err_{odabrani_id}")
        else: 
            st.info("Nema dokumenata u bazi.")

        # =========================================================================
    # 📜 EKRAN 3: MATIČNE KNJIGE (POTPUNO OPTIMIZIRANO I UBRZANO)
    # =========================================================================
    elif izbor == "📜 Matične knjige":
        st.title("📜 Matične knjige")
        
        # 1. BRZINA: Iz baze vučemo samo ID i naziv datoteke. Teški Base64 spava u bazi!
        cursor.execute("SELECT id, split_part(datoteka, '|||', 1) FROM povijest_dokumenata WHERE id_cestice = 777777 ORDER BY id DESC")
        rezultati_baze = cursor.fetchall()

        if rezultati_baze:
            # Stvaramo čisti rječnik: ključ je naziv datoteke, vrijednost je ID u bazi
            mat_mape_id = {r[1]: r[0] for r in rezultati_baze if r[1] != ""}
            mat_imena = list(mat_mape_id.keys())
            
            odabrana_mat_ime = st.selectbox("📜 Odaberite matičnu knjigu:", [""] + mat_imena)
            
            if odabrana_mat_ime != "":
                odabrani_id = mat_mape_id[odabrana_mat_ime]
                
                with st.spinner("⏳ Dohvaćam matičnu knjigu iz arhive..."):
                    # LAZY LOADING: Povlačimo cijeli Base64 string isključivo za odabrani ID
                    cursor.execute("SELECT datoteka FROM povijest_dokumenata WHERE id = %s", (odabrani_id,))
                    rezultat_doc = cursor.fetchone()
                
                if rezultat_doc and rezultat_doc[0] and "|||" in rezultat_doc[0]:
                    naziv_datoteke, b64_sadrzaj = rezultat_doc[0].split("|||", 1)
                    binarni_podaci = base64.b64decode(b64_sadrzaj)
                    
                    st.write("---")
                    
                    # A. Ako je datoteka SLIKA (.jpg, .png)
                    if naziv_datoteke.lower().endswith(('.jpg', '.jpeg', '.png')):
                        st.html("<style>div[data-testid='stImage'] img {pointer-events: none !important;}</style>")
                        st.image(binarni_podaci, width='stretch')  # 🔥 PAŽLJIVO UKLJUČEN width='stretch'
                        st.download_button(label="📥 Preuzmi ovu sliku", data=binarni_podaci, file_name=naziv_datoteke, mime="image/jpeg", use_container_width=True, key=f"dl_mat_img_{odabrani_id}")
                    
                    # B. Ako je datoteka PDF (Uzimamo prvu stranicu iz liste i crtamo je kao sliku)
                    elif naziv_datoteke.lower().endswith('.pdf'):
                        try:
                            from pdf2image import convert_from_bytes
                            import io
                            
                            stranice = convert_from_bytes(binarni_podaci, dpi=130)
                            if stranice:
                                img_byte_arr = io.BytesIO()
                                # Uzimamo točno prvu stranicu iz liste slika
                                s_stranica = stranice[0]
                                s_stranica.save(img_byte_arr, format='JPEG', quality=85)
                                cista_slika = img_byte_arr.getvalue()
                                
                                # Prikaz prve stranice na ekranu - stabilno za Chrome i Firefox
                                st.html("<style>div[data-testid='stImage'] img {pointer-events: none !important;}</style>")
                                st.image(cista_slika, width='stretch')  # 🔥 PAŽLJIVO UKLJUČEN width='stretch'
                                
                                # Gumb za preuzimanje cijelog PDF dokumenta
                                st.download_button(label="📥 Preuzmi cijelu matičnu knjigu (PDF)", data=binarni_podaci, file_name=naziv_datoteke, mime="application/pdf", use_container_width=True, key=f"dl_mat_pdf_{odabrani_id}")
                        except Exception as e:
                            st.error(f"⚠️ Došlo je do greške pri iscrtavanju: {e}")
                            st.download_button("📥 Otvori / Preuzmi PDF", binarni_podaci, file_name=naziv_datoteke, mime="application/pdf", use_container_width=True, key=f"dl_mat_err_{odabrani_id}")
        else: 
            st.info("Nema matičnih knjiga u bazi.")

       # =========================================================================
    # 📂 EKRAN 4: DOKUMENTACIJA O DIOBI
    # =========================================================================
    elif izbor == "📂 Dokumenti":
        st.title("📂 Dokumentacija o Diobi")
        
        # 1. BRZINA: Iz baze vučemo samo ID i naziv datoteke. Teški Base64 spava u bazi!
        cursor.execute("SELECT id, split_part(datoteka, '|||', 1) FROM povijest_dokumenata WHERE vrsta_lista = 'Poslani dokument' ORDER BY id DESC")
        rezultati_baze = cursor.fetchall()

        if rezultati_baze:
            # Stvaramo čisti rječnik: ključ je naziv datoteke, vrijednost je ID u bazi
            doc_mape_id = {r[1]: r[0] for r in rezultati_baze if r[1] != ""}
            p_imena = list(doc_mape_id.keys())
            
            odabir_doc = st.selectbox("Odaberite dokument:", [""] + p_imena)
            
            if odabir_doc != "":
                odabrani_id = doc_mape_id[odabir_doc]
                
                with st.spinner("⏳ Dohvaćam dokument iz arhive..."):
                    # LAZY LOADING: Povlačimo cijeli Base64 string isključivo za odabrani ID
                    cursor.execute("SELECT datoteka FROM povijest_dokumenata WHERE id = %s", (odabrani_id,))
                    rezultat_doc = cursor.fetchone()
                
                if rezultat_doc and rezultat_doc[0] and "|||" in rezultat_doc[0]:
                    # Točno izvlačimo naziv i Base64 sadržaj iz baze podataka
                    naziv_datoteke, b64_sadrzaj = rezultat_doc[0].split("|||", 1)
                    binarni_podaci = base64.b64decode(b64_sadrzaj)
                    
                    st.write("---")
                    
                    # A. Ako je datoteka SLIKA (.jpg, .png)
                    if naziv_datoteke.lower().endswith(('.jpg', '.jpeg', '.png')):
                        st.html("<style>div[data-testid='stImage'] img {pointer-events: none !important;}</style>")
                        st.image(binarni_podaci, width='stretch')
                        st.download_button(label="📥 Preuzmi ovu sliku", data=binarni_podaci, file_name=naziv_datoteke, mime="image/jpeg", use_container_width=True, key=f"dl_doc_img_{odabrani_id}")
                    
                    # B. Ako je datoteka PDF (Uzimamo prvu stranicu iz liste [0] i crtamo je kao sliku)
                    elif naziv_datoteke.lower().endswith('.pdf'):
                        try:
                            from pdf2image import convert_from_bytes
                            import io
                            
                            stranice = convert_from_bytes(binarni_podaci, dpi=130)
                            if stranice:
                                img_byte_arr = io.BytesIO()
                                # POPRAVLJENO: Uzimamo točno prvu stranicu [0] iz liste slika
                                stranice[0].save(img_byte_arr, format='JPEG', quality=85)
                                cista_slika = img_byte_arr.getvalue()
                                
                                # Prikaz prve stranice na ekranu - stabilno za Chrome i Firefox
                                st.html("<style>div[data-testid='stImage'] img {pointer-events: none !important;}</style>")
                                st.image(cista_slika, width='stretch')
                                
                                # Gumb za preuzimanje cijelog PDF dokumenta
                                st.download_button(label="📥 Preuzmi cijeli PDF dokument", data=binarni_podaci, file_name=naziv_datoteke, mime="application/pdf", use_container_width=True, key=f"dl_doc_pdf_{odabrani_id}")
                        except Exception as e:
                            st.error(f"⚠️ Došlo je do greške pri iscrtavanju: {e}")
                            st.download_button("📥 Otvori / Preuzmi PDF", binarni_podaci, file_name=naziv_datoteke, mime="application/pdf", use_container_width=True, key=f"dl_doc_err_{odabrani_id}")
                    
                    # C. Prikaz Office dokumenata (Excel, Word)
                    elif naziv_datoteke.lower().endswith(('.xlsx', '.xls', '.docx', '.doc')):
                        st.download_button(label=f"📥 Preuzmi: {naziv_datoteke}", data=binarni_podaci, file_name=naziv_datoteke, key=f"dl_office_{odabrani_id}", use_container_width=True)
        else: 
            st.info("Nema dokumenata.")

    elif izbor == "👥 Odabir čestica":
        import nasljednici
        nasljednici.prikazi_ekran_nasljednika(cursor, conn)

    elif izbor == "⚖️ Upravljanje Diobom":
        import dioba_admin
        dioba_admin.prikazi_ekran_administracije(cursor, conn)



