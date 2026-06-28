import streamlit as st


def prikazi_unos(conn, cursor, sva_p, p_dict):
    tab1, tab2 = st.tabs(["➕ Čestice (Unos)", "📜 Stari Listovi"])

    # --- TAB 1: UNOS ČESTICA ---
    with tab1:
        if sva_p:
            with st.form("f_c", clear_on_submit=True):
                p_odabir = st.selectbox(
                    "Područje:", list(p_dict.keys()), key="unos_p_odabir"
                )
                b_cestice = st.text_input("Broj čestice:")
                kategorije_sifre = [
                "— Bez šifre —",    
                "Čestica na drugim posjedovnim listovima",
                "Usmeno dogovoreno (nije prepisano)",
                "Čestica na starim listovima"
                ]
                odabrana_sifra = st.selectbox("Kategorija čestice:", kategorije_sifre)
                k_opcina = st.text_input("Katastarska općina (K.O.):")
                pov = st.number_input("Površina (m²):", min_value=0, step=1)
                zk = st.text_input("ZK Uložak:")
                dnevnik = st.text_input("Broj dnevnika (Z-broj):")
                oznaka = st.text_input("Oznaka zemljišta:")
                naziv_z = st.text_input("Naziv zemljišta:")
                nap = st.text_area("Interna napomena:")

                if st.form_submit_button("Spremi Novu Česticu") and b_cestice:
                    try:
                        # POPRAVLJENO: ? zamijenjen s %s za Supabase (PostgreSQL)
                        cursor.execute(
                            """
                            INSERT INTO cestice (broj_cestice, zk_ulozak, broj_zadnjeg_dnevnika, oznaka_zemljista, naziv_zemljista, napomena, povrsina, katastarska_opcina, sifra, id_podrucja) 
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            """,
                            (
                                b_cestice,
                                zk if zk else None,
                                dnevnik if dnevnik else None,
                                oznaka if oznaka else None,
                                naziv_z if naziv_z else None,
                                nap if nap else None,
                                pov if pov > 0 else None,
                                k_opcina if k_opcina else None,
                                None if odabrana_sifra == "— Bez šifre —" else odabrana_sifra,
                                p_dict[p_odabir],
                            ),
                        )
                        conn.commit()
                        st.success("Čestica uspješno spremljena!")
                        st.rerun()
                    except Exception as e:
                        if conn:
                            conn.rollback()
                        
                        # Provjera jedinstvenosti broja čestice
                        if "unique constraint" in str(e).lower() or "duplicate" in str(e).lower():
                            st.error("❌ Ova čestica već postoji u bazi podataka!")
                        else:
                            st.error(f"❌ Greška prilikom spremanja: {e}")
        else:
            st.info("Prvo dodajte područje s lijeve strane.")

    # --- TAB 2: UNOS STARIH LISTOVA ---
        # --- TAB 2: UNOS STARIH LISTOVA (Supabase Storage Uploader) ---
        # --- TAB 2: UNOS STARIH LISTOVA (Pretvaranje datoteke u SQL tekst - Base64) ---
    with tab2:
        st.subheader("Povezivanje povijesnih listova s česticama")
        
        cursor.execute("SELECT id, broj_cestice FROM cestice")
        sve_c_za_doc = cursor.fetchall()
        
        if sve_c_za_doc:
            c_doc_dict = {broj: int(id) for id, broj in sve_c_za_doc}
            
            with st.form("f_d", clear_on_submit=True):
                c_odabir = st.selectbox(
                    "Poveži s česticom:", list(c_doc_dict.keys()), key="doc_c_odabir"
                )
                v_lista = st.selectbox(
                    "Vrsta dokumenta:", ["Posjedovni list", "Vlasnički list"]
                )
                br_lista = st.text_input("Broj lista / uložka:")
                starost = st.text_input("Starost / Godina:")
                vlasnik = st.text_input("Upisani vlasnik / posjednik:")
                p_nap = st.text_area("Povijesna napomena:")
                
                # Uploader ostaje isti - jednostavan izbor datoteke
                ucitana_datoteka = st.file_uploader(
                    "Odaberi sliku ili PDF dokument s računala/mobitela:", 
                    type=["jpg", "jpeg", "png", "pdf"]
                )

                if st.form_submit_button("Spremi Dokument"):
                    if not ucitana_datoteka:
                        st.error("❌ Morate odabrati datoteku prije spremanja!")
                    else:
                        try:
                            import base64
                            # 1. Čitamo datoteku i pretvaramo je u običan tekstualni niz
                            bajtovi = ucitana_datoteka.read()
                            tekstualni_b64 = base64.b64encode(bajtovi).decode('utf-8')
                            
                            # 2. Spajamo naziv datoteke s njenim sadržajem u jedan tekst
                            # npr: "slika.jpg|||OVDJE_IDE_CILI_TEKST_SLIKE"
                            kodirani_zapis = f"{ucitana_datoteka.name}|||{tekstualni_b64}"
                            
                            pravi_id_cestice = int(c_doc_dict[c_odabir])
                            
                            # 3. Upisujemo SVE u SQL tablicu odjednom (Preko provjerenog psycopg2)
                            cursor.execute(
                                """
                                INSERT INTO povijest_dokumenata 
                                (id_cestice, vrsta_lista, broj_lista_korisnika, starost_godina, upisani_vlasnik_posjednik, povijesna_napomena, datoteka) 
                                VALUES (%s, %s, %s, %s, %s, %s, %s)
                                """,
                                (
                                    pravi_id_cestice,
                                    v_lista,
                                    br_lista,
                                    starost,
                                    vlasnik,
                                    p_nap,
                                    kodirani_zapis,  # <-- Ovdje sada spremamo cijelu datoteku kao tekst!
                                ),
                            )
                            conn.commit()
                            st.success(f"✅ Uspješno spremljen dokument u bazu za česticu {c_odabir}!")
                            st.rerun()
                            
                        except Exception as e:
                            if conn:
                                conn.rollback()
                            st.error(f"❌ Greška prilikom spremanja u SQL bazu: {e}")
