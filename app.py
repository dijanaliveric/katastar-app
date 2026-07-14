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
# 🏛️ UNUTARNJI BOČNI IZBORNIK PREKO ST.COLUMNS (ZAMJENA ZA SIDEBAR)
# =========================================================================
popis_opcija = ["🗺️ Pregled i pretraga čestica", "📋 Posjedovni listovi", "📜 Matične knjige", "📂 Dokumenti"]

glavni_col1, glavni_col2 = st.columns([1, 4])

with glavni_col1:
    st.markdown("### 🧭 Navigacija")
    izbor = st.radio("Odaberite odjeljak:", popis_opcija, label_visibility="collapsed")
    
    st.markdown("[🌍 Pozicija čestice na karti](https://oss.uredjenazemlja.hr)")
    st.write("---")
    
          # --- BRZI FILTERI UNUTAR LIJEVOG STUPCA ---
    if izbor == "🗺️ Pregled i pretraga čestica":
        
        trenutna_c = st.session_state.get("odabrana_c_kljuc", " 🔍 SVE ")
        
        if trenutna_c == " 🔍 SVE ":      
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
        
       # with col_f2: odabrana_c = st.selectbox("Odaberi broj čestice:", ["-- Prikaži sve čestice --"] + list(c_dict.keys()), key="odabrana_c_kljuc")

        popis_opcija_c = [" 🔍 SVE "] + list(c_dict.keys())

        with col_f2: 
            odabrana_c = st.selectbox(
                "Odaberi broj čestice:", 
                popis_opcija_c, 
                key="odabrana_c_kljuc"
            )


        st.write("---")
        
        if odabrana_c != " 🔍 SVE ":
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
            cursor.execute("SELECT vrsta_lista, broj_lista_korisnika, starost_godina, upisani_vlasnik_posjednik, povijesna_napomena, datoteka FROM povijest_dokumenata WHERE id_cestice = %s", (c_dict[odabrana_c],))
            for v, br, st_g, vl, p_n, dat in cursor.fetchall():
                with st.expander(f"📄 {v} br. {br} ({st_g})"):
                    st.write(f"👤 {vl} | 💬 {p_n}")
                    if dat and "|||" in dat:
                        ime, b64_kod = dat.split("|||", 1)
                        st.html("<style>div[data-testid='stImage'] img {pointer-events: none !important;}</style>")
                        if ime.lower().endswith(('.jpg', '.jpeg', '.png')): st.image(base64.b64decode(b64_kod), width='stretch')
        else:
                   
                
            upit_tablica = """
                SELECT c.broj_cestice, c.zk_ulozak, c.katastarska_opcina, 
                       p.naziv_podrucja, c.naziv_zemljista, c.oznaka_zemljista, c.povrsina 
                FROM cestice c 
                JOIN podrucja p ON c.id_podrucja = p.id
                WHERE c.id NOT IN (999999, 777777)
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
            
            

        # --- 📋 EKRAN 2: POSJEDOVNI LISTOVI ---
    elif izbor == "📋 Posjedovni listovi":
        st.title("📋 Katastarski Posjedovni Listovi")
        cursor.execute("SELECT datoteka FROM povijest_dokumenata WHERE vrsta_lista = 'Posjedovni list' AND broj_lista_korisnika NOT ILIKE '%Ne postoji podatak o identifikaciji%'")
        svi_pl = [r[0] for r in cursor.fetchall() if r and "|||" in r[0]]

        if svi_pl:
            #  indeks [0] da dobijemo čisto ime za padajući izbornik
            pl_imena = [f.split("|||", 1)[0] for f in svi_pl]
            odabrani_pl_ime = st.selectbox("📄 Odaberite posjedovni list:", [""] + pl_imena)
            if odabrani_pl_ime != "":
                indeks = pl_imena.index(odabrani_pl_ime)
                #  indeks [1] za  Base64 kod slike
                naziv_datoteke = svi_pl[indeks].split("|||", 1)[0]
                b64_sadrzaj = svi_pl[indeks].split("|||", 1)[1]
                
                st.write("---")
                if naziv_datoteke.lower().endswith(('.jpg', '.jpeg', '.png')):
                    st.image(base64.b64decode(b64_sadrzaj), width='stretch')
                elif naziv_datoteke.lower().endswith('.pdf'):
                    pdf_prikaz = f'<iframe src="data:application/pdf;base64,{b64_sadrzaj}#toolbar=0&navpanes=0" width="100%" height="800" type="application/pdf"></iframe>'
                    st.markdown(pdf_prikaz, unsafe_allow_html=True)

        else: st.info("Nema dokumenata u bazi.")

    # --- 📜 EKRAN 3: MATIČNE KNJIGE ----
    elif izbor == "📜 Matične knjige":
        st.title("📜 Arhiv Matičnih Knjiga")
        st.caption("🏛️ *Izvor dokumentacije: Državni arhiv u Zadru*")

        cursor.execute("SELECT datoteka FROM povijest_dokumenata WHERE vrsta_lista = 'Matična knjiga'")
        sve_mk = [r[0] for r in cursor.fetchall() if r and "|||" in r[0]]

        if sve_mk:
            mk_imena = []
            for f in sve_mk:
                # indeks [0] iz splita da dobijemo čisto ime datoteke, pa čistimo ekstenziju
                ime_datoteke = f.split("|||", 1)[0]
                cisto_ime = ime_datoteke.rsplit('.', 1)[0] if '.' in ime_datoteke else ime_datoteke
                mk_imena.append(f"Arhiv: {cisto_ime.upper()} MLINAR")
                
            odabir_osobe = st.selectbox("👤 Odaberite zapis za pregled:", [""] + mk_imena)
            if odabir_osobe != "":
                indeks = mk_imena.index(odabir_osobe)
                #  indeks [1] za čisti Base64 kod slike predka
                b64_sadrzaj = sve_mk[indeks].split("|||", 1)[1]
                st.image(base64.b64decode(b64_sadrzaj), width='stretch')
        else: st.info("Nema matičnih knjiga.")

    # --- 📂 EKRAN 4: DOKUMENTI OD RODBINE ---
    elif izbor == "📂 Dokumenti":
        st.title("📂 Dokumentacija o Diobi")
        cursor.execute("SELECT datoteka FROM povijest_dokumenata WHERE vrsta_lista = 'Poslani dokument'")
        svi_pos = [r[0] for r in cursor.fetchall() if r and "|||" in r[0]]

        if svi_pos:
            p_imena = [f.split("|||", 1)[0] for f in svi_pos]
            odabir_doc = st.selectbox("Odaberite dokument:", [""] + p_imena)
            if odabir_doc != "":
                indeks = p_imena.index(odabir_doc)
                # POPRAVLJENO: Točno raspakiravamo naziv [0] i Base64 kod [1] iz baze
                naziv_datoteke = svi_pos[indeks].split("|||", 1)[0]
                b64_sadrzaj = svi_pos[indeks].split("|||", 1)[1]
                
                if naziv_datoteke.lower().endswith(('.jpg', '.jpeg', '.png')):
                    st.image(base64.b64decode(b64_sadrzaj), width='stretch')
                elif naziv_datoteke.lower().endswith('.pdf'):
                    pdf_prikaz = f'<iframe src="data:application/pdf;base64,{b64_sadrzaj}#toolbar=0" width="100%" height="800" type="application/pdf"></iframe>'
                    st.markdown(pdf_prikaz, unsafe_allow_html=True)
                elif naziv_datoteke.lower().endswith(('.xlsx', '.xls', '.docx', '.doc')):
                    st.download_button(label=f"📥 Preuzmi: {naziv_datoteke}", data=base64.b64decode(b64_sadrzaj), file_name=naziv_datoteke, key=f"dl_{naziv_datoteke}")
        else: st.info("Nema dokumenata.")

conn.close()

