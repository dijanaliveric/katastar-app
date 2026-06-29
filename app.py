import os
import psycopg2
import streamlit as st
import base64
import warnings

# 1. POSTAVKE STRANICE
st.set_page_config(page_title="Katastar Arhiva - Pregled", layout="wide")
warnings.filterwarnings("ignore", category=UserWarning)

# --- 🔒 TOTALNO BRISANJE GORNJE TRAKE I ZAŠTITA SLIKA ---
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
        else: st.error("❌ Nevazeće lozinke.")
    st.stop()

# --- SPAJANJE NA BAZU S TIMEOUTOM ---
conn = psycopg2.connect(
    host=st.secrets["baza"]["host"], port=st.secrets["baza"]["port"],
    database=st.secrets["baza"]["database"], user=st.secrets["baza"]["user"],
    password=st.secrets["baza"]["password"], sslmode=st.secrets["baza"]["sslmode"],
    options="-c statement_timeout=5000"
)
cursor = conn.cursor()


# =========================================================================
# 🏛️ NAŠ VLASTITI UNUTARNJI BOČNI IZBORNIK PREKO ST.COLUMNS (ZAMJENA ZA SIDEBAR)
# =========================================================================
popis_opcija = ["🗺️ Pregled i pretraga čestica", "📋 Posjedovni listovi", "📜 Matične knjige", "📂 Dokumenti"]

# Dijelimo cijeli ekran na dva dijela: Lijevi (Izbornik) i Desni (Sadržaj)
glavni_col1, glavni_col2 = st.columns([1, 4])

with glavni_col1:
    st.markdown("### 🧭 Navigacija")
    izbor = st.radio("Odaberite odjeljak:", popis_opcija, label_visibility="collapsed")
    st.write("---")

# =========================================================================
# 🚀 DESNI DIO: LOGIKA PRIKAZA EKRANA OVISNO O ODABIRU
# =========================================================================
with glavni_col2:
    # --- 🗺️ EKRAN 1: PREGLED ČESTICA ---
    if izbor == "🗺️ Pregled i pretraga čestica":
        st.title("🗺️ Obiteljska Arhiva Katastra")
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
                    st.write(f"👤 {vl} | 💬 {p_n}")
                    if dat and "|||" in dat:
                        ime, b64_kod = dat.split("|||", 1)
                        st.html("<style>div[data-testid='stImage'] img {pointer-events: none !important;}</style>")
                        if ime.lower().endswith(('.jpg', '.jpeg', '.png')): st.image(base64.b64decode(b64_kod), use_container_width=True)
        else:
            import pandas as pd
            #upit = "SELECT c.broj_cestice, c.zk_ulozak, c.katastarska_opcina, p.naziv_podrucja, c.povrsina FROM cestice c JOIN podrucja p ON c.id_podrucja = p.id"
            #df = pd.read_sql_query(upit, conn)
            #st.dataframe(df, width='stretch', hide_index=True)
                    
            # NOVO: Čitamo iz našeg novog, pametnog SQL pogleda koji sam skriva lažne čestice
            upit = "SELECT c.broj_cestice, c.zk_ulozak, c.katastarska_opcina, p.naziv_podrucja, c.povrsina FROM cestice c JOIN podrucja p ON c.id_podrucja = p.id WHERE c.id_podrucja = %s"
            df = pd.read_sql_query(upit, conn, params=[p_dict[odabrano_p]])
            st.dataframe(df, width='stretch', hide_index=True)



        # --- 📋 EKRAN 2: POSJEDOVNI LISTOVI ---
    elif izbor == "📋 Posjedovni listovi":
        st.title("📋 Katastarski Posjedovni Listovi")
        cursor.execute("SELECT datoteka FROM povijest_dokumenata WHERE vrsta_lista = 'Posjedovni list'")
        svi_pl = [r[0] for r in cursor.fetchall() if r and "|||" in r[0]]

        if svi_pl:
            # POPRAVLJENO: Uzimamo indeks [0] da dobijemo čisto ime za padajući izbornik
            pl_imena = [f.split("|||", 1)[0] for f in svi_pl]
            odabrani_pl_ime = st.selectbox("📄 Odaberite posjedovni list:", [""] + pl_imena)
            if odabrani_pl_ime != "":
                indeks = pl_imena.index(odabrani_pl_ime)
                # POPRAVLJENO: Uzimamo indeks [1] za čisti Base64 kod slike
                b64_sadrzaj = svi_pl[indeks].split("|||", 1)[1]
                st.image(base64.b64decode(b64_sadrzaj), use_container_width=True)
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
                # POPRAVLJENO: Uzimamo indeks [0] iz splita da dobijemo čisto ime datoteke, pa čistimo ekstenziju
                ime_datoteke = f.split("|||", 1)[0]
                cisto_ime = ime_datoteke.rsplit('.', 1)[0] if '.' in ime_datoteke else ime_datoteke
                mk_imena.append(f"Arhiv: {cisto_ime.upper()} MLINAR")
                
            odabir_osobe = st.selectbox("👤 Odaberite zapis za pregled:", [""] + mk_imena)
            if odabir_osobe != "":
                indeks = mk_imena.index(odabir_osobe)
                # POPRAVLJENO: Uzimamo indeks [1] za čisti Base64 kod slike predka
                b64_sadrzaj = sve_mk[indeks].split("|||", 1)[1]
                st.image(base64.b64decode(b64_sadrzaj), use_container_width=True)
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
                    st.image(base64.b64decode(b64_sadrzaj), use_container_width=True)
                elif naziv_datoteke.lower().endswith('.pdf'):
                    pdf_prikaz = f'<iframe src="data:application/pdf;base64,{b64_sadrzaj}#toolbar=0" width="100%" height="800" type="application/pdf"></iframe>'
                    st.markdown(pdf_prikaz, unsafe_allow_html=True)
                elif naziv_datoteke.lower().endswith(('.xlsx', '.xls', '.docx', '.doc')):
                    st.download_button(label=f"📥 Preuzmi: {naziv_datoteke}", data=base64.b64decode(b64_sadrzaj), file_name=naziv_datoteke, key=f"dl_{naziv_datoteke}")
        else: st.info("Nema dokumenata.")

conn.close()

