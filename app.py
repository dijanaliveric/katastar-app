import os
import psycopg2
import streamlit as st
import base64
import warnings

# 1. GLAVNE POSTAVKE
st.set_page_config(page_title="Katastar Arhiva", layout="wide")
warnings.filterwarnings("ignore", category=UserWarning)

# --- JEDNOSTAVNA ZAŠTITA ZA ULAZ ---
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
        else:
            st.error("❌ Nevazeće lozinke.")
    st.stop()

# --- SPAJANJE NA BAZU S TIMEOUTOM ---
conn = psycopg2.connect(
    host=st.secrets["baza"]["host"],
    port=st.secrets["baza"]["port"],
    database=st.secrets["baza"]["database"],
    user=st.secrets["baza"]["user"],
    password=st.secrets["baza"]["password"],
    sslmode=st.secrets["baza"]["sslmode"],
    options="-c statement_timeout=5000"
)
cursor = conn.cursor()

# --- 🔒 MAKSIMALNA ZAŠTITA SLIKA (CSS ZABRANA SPREMANJA) ---
st.markdown("<style>img {-webkit-touch-callout:none;-webkit-user-select:none;user-select:none;pointer-events:none;}</style>", unsafe_allow_html=True)

# =========================================================================
# 🧭 ELEGANTAN BOČNI IZBORNIK (SIDEBAR) - UNIŠTAVA POPUSH-PROZORE
# =========================================================================
st.sidebar.title("🧭 Arhiva Navigacija")
izbor = st.sidebar.radio(
    "Odaberite što želite gledati:",
    ["🗺️ Pregled i pretraga čestica", "📋 Opći posjedovni listovi", "📜 Matične knjige", "📂 Dokumenti od rodbine"]
)

# --- OPCIJA 1: PREGLED ČESTICA ---
if izbor == "🗺️ Pregled i pretraga čestica":
    st.title("🗺️ Obiteljska Arhiva Zemljišta i Čestica")
    
    # Uploader za rodbinu na vrhu
    if "uploader_kljuc" not in st.session_state: st.session_state["uploader_kljuc"] = 0
    up_doc = st.file_uploader("Učitaj novi dokument:", type=["png", "jpg", "jpeg", "pdf"], key=f"up_{st.session_state['uploader_kljuc']}")
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

    if odabrano_p == "Sva područja": cursor.execute("SELECT id, broj_cestice FROM cestice")
    else: cursor.execute("SELECT id, broj_cestice FROM cestice WHERE id_podrucja = %s", (p_dict[odabrano_p],))
    c_dict = {broj: id for id, broj in cursor.fetchall()}
    with col_f2: odabrana_c = st.selectbox("Odaberi broj čestice:", ["-- Prikaži sve čestice --"] + list(c_dict.keys()))

    st.write("---")
    if odabrana_c != "-- Prikaži sve čestice --":
        cursor.execute("SELECT c.zk_ulozak, c.broj_zadnjeg_dnevnika, c.oznaka_zemljista, c.naziv_zemljista, c.napomena, c.povrsina, p.naziv_podrucja, c.katastarska_opcina, c.sifra FROM cestice c JOIN podrucja p ON c.id_podrucja = p.id WHERE c.id = %s", (c_dict[odabrana_c],))
        zk, dn, oz, nz, nap, pov, lok, ko, sif = cursor.fetchone()
        st.markdown(f"### 📍 Podaci za česticu: **{odabrana_c}** ({lok})")
        c1, c2, c3 = st.columns(3)
        c1.info(f"**📑 K.O.:** {ko}\n\n**🔢 ZK Uložak:** {zk}")
        c2.info(f"**🌿 Oznaka:** {oz}\n\n**🗺️ Naziv:** {nz}")
        c3.success(f"**📐 Površina:**\n\n### {pov} m²")
        st.markdown(f"**🏷️ Kategorija:** `{sif if sif else 'Bez šifre'}`")
        if nap: st.info(f"📝 Napomena: {nap}")
        
        st.write("---")
        st.markdown("### ⏳ Povijesna Arhiva Listova")
        cursor.execute("SELECT vrsta_lista, broj_lista_korisnika, starost_godina, upisani_vlasnik_posjednik, povijesna_napomena, datoteka FROM povijest_dokumenata WHERE id_cestice = %s", (c_dict[odabrana_c],))
        for v, br, st_g, vl, p_n, dat in cursor.fetchall():
            with st.expander(f"📄 {v} br. {br} ({st_g})"):
                st.write(f"👤 Korisnik: {vl} | 💬 {p_n}")
                if dat and "|||" in dat:
                    ime, b64_kod = dat.split("|||", 1)
                    if ime.lower().endswith(('.jpg', '.jpeg', '.png')): st.image(base64.b64decode(b64_kod), use_container_width=True)
    else:
        import pandas as pd
        upit = "SELECT c.broj_cestice, c.zk_ulozak, c.katastarska_opcina, p.naziv_podrucja, c.povrsina FROM cestice c JOIN podrucja p ON c.id_podrucja = p.id"
        df = pd.read_sql_query(upit, conn)
        st.dataframe(df, width='stretch', hide_index=True)

# --- OPCIJA 2: VELIKI PREGLED POSJEDOVNIH LISTOVA PREKO CIJELOG EKRANA ---
elif izbor == "📋 Posjedovni listovi":
    st.title("📋 Katastarski Posjedovni Listovi")
    cursor.execute("SELECT datoteka FROM povijest_dokumenata WHERE vrsta_lista = 'Posjedovni list'")
    # Izvlačimo čisti tekst iz torke pomoću r[0]
    svi_pl = [r[0] for r in cursor.fetchall() if r and r[0] and "|||" in r[0]]
    
    if svi_pl:
        pl_imena = [f.split("|||", 1)[0] for f in svi_pl]
        odabrani_pl_ime = st.selectbox("📄 Odaberite stranicu posjedovnog lista za pregled:", [""] + pl_imena)
        
        if odabrani_pl_ime != "":
            indeks = pl_imena.index(odabrani_pl_ime)
            st.write("---")
            b64_sadrzaj = svi_pl[indeks].split("|||", 1)[1]
            st.image(base64.b64decode(b64_sadrzaj), use_container_width=True)
    else: 
        st.info("U bazi podataka trenutno nema unesenih općih posjedovnih listova.")

# --- OPCIJA 3: VELIKI PREGLED MATIČNIH KNJIGA PREKO CIJELOG EKRANA ---
elif izbor == "📜 Matične knjige":
    st.title("📜 Arhiv Matičnih Knjiga (Državni Arhiv Zadar)")
    cursor.execute("SELECT datoteka FROM povijest_dokumenata WHERE vrsta_lista = 'Matična knjiga'")
    sve_mk = [r[0] for r in cursor.fetchall() if r and r[0] and "|||" in r[0]]
    
    if sve_mk:
        mk_imena = []
        for f in sve_mk:
            ime_datoteke = f.split("|||", 1)[0]
            cisto_ime = ime_datoteke.rsplit('.', 1)[0] if '.' in ime_datoteke else ime_datoteke
            mk_imena.append(f"Arhiv: {cisto_ime.upper()}")
            
        odabir_osobe = st.selectbox("👤 Odaberite zapis za pregled:", [""] + mk_imena)
        
        if odabir_osobe != "":
            indeks = mk_imena.index(odabir_osobe)
            st.write("---")
            b64_sadrzaj = sve_mk[indeks].split("|||", 1)[1]
            st.image(base64.b64decode(b64_sadrzaj), use_container_width=True)
    else: 
        st.info("U bazi podataka trenutno nema unesenih matičnih knjiga.")

# --- OPCIJA 4: PREGLED DOKUMENATA OD RODBINE PREKO CIJELOG EKRANA ---
elif izbor == "📂 Dokumenti":
    st.title("📂 Pregled Obiteljskih Dokumenata")
    cursor.execute("SELECT datoteka FROM povijest_dokumenata WHERE vrsta_lista = 'Poslani dokument'")
    svi_pos = [r[0] for r in cursor.fetchall() if r and r[0] and "|||" in r[0]]
    
    if svi_pos:
        p_imena = [f.split("|||", 1)[0] for f in svi_pos]
        odabir_doc = st.selectbox("Odaberite dokument:", [""] + p_imena)
        
        if odabir_doc != "":
            indeks = p_imena.index(odabir_doc)
            st.write("---")
            naziv_datoteke, b64_sadrzaj = svi_pos[indeks].split("|||", 1)
            
                       # --- POPRAVLJENO: Razlikujemo slike, PDF-ove, Excel i Word formate ---
            if naziv_datoteke.lower().endswith(('.jpg', '.jpeg', '.png')):
                # Slike prikazujemo u punoj veličini
                st.image(base64.b64decode(b64_sadrzaj), use_container_width=True)
                
            elif naziv_datoteke.lower().endswith('.pdf'):
                # PDF ugrađujemo na ekran
                pdf_prikaz = f'<iframe src="data:application/pdf;base64,{b64_sadrzaj}#toolbar=0&navpanes=0" width="100%" height="800" type="application/pdf"></iframe>'
                st.markdown(pdf_prikaz, unsafe_allow_html=True)
                
            elif naziv_datoteke.lower().endswith(('.xlsx', '.xls', '.docx', '.doc')):
                # Za Excel i Word nudimo siguran gumb za download jer se ne mogu nacrtati kao slike
                izvorni_bajtovi = base64.b64decode(b64_sadrzaj)
                
                # Određujemo točan MIME tip ovisno o tome je li Word ili Excel
                if naziv_datoteke.lower().endswith(('.xlsx', '.xls')):
                    m_tip = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    ikona_gumba = "📊"
                else:
                    m_tip = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    ikona_gumba = "📝"
                
                st.info(f"{ikona_gumba} Datoteka '{naziv_datoteke}' je uredski dokument. Kliknite ispod za preuzimanje i pregled:")
                st.download_button(
                    label=f"{ikona_gumba} Preuzmi: {naziv_datoteke}",
                    data=izvorni_bajtovi,
                    file_name=naziv_datoteke,
                    mime=m_tip,
                    key=f"dl_rodbina_{naziv_datoteke}"
                )
            else:
                st.warning(f"Format datoteke '{naziv_datoteke}' nije podržan za izravan pregled.")

    else: 
        st.info("Rodbina još nije poslala nijedan dokument preko gornjeg uploadera.")

conn.close()
