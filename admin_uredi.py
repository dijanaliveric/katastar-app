import streamlit as st


def prikazi_uredivanje(conn, cursor, c_glavni_dict, p_dict, p_obrnuti_dict):
    # =========================================================================
    # DIO 1: IZMJENA PODATAKA POSTOJEĆE ČESTICE (Vaš postojeći kôd)
    # =========================================================================
    st.subheader("✍️ Izmjena podataka postojeće čestice")

    if c_glavni_dict:
        odabrana_za_izmjenu = st.selectbox(
            "Odaberi česticu koju želiš izmijeniti:",
            list(c_glavni_dict.keys()),
            key="izbornik_za_izmjenu",
        )
        id_za_izmjenu = c_glavni_dict[odabrana_za_izmjenu]

        cursor.execute(
            "SELECT zk_ulozak, broj_zadnjeg_dnevnika, oznaka_zemljista, naziv_zemljista, napomena, povrsina, katastarska_opcina, id_podrucja, sifra FROM cestice WHERE id = %s",
            (id_za_izmjenu,),
        )
        e_zk, e_dnevnik, e_oznaka, e_naziv, e_nap, e_pov, e_ko, e_pod_id, e_sifra = (
            cursor.fetchone()
        )

        with st.form("forma_izmjene_podataka"):
            u_ko = st.text_input(
                "Katastarska općina (K.O.):", value=e_ko if e_ko else ""
            )
            u_pov = st.number_input(
                "Površina (m²):",
                min_value=0,
                value=int(e_pov) if e_pov else 0,
                step=1,
            )
            u_zk = st.text_input("ZK Uložak:", value=e_zk if e_zk else "")
            u_dnevnik = st.text_input(
                "Broj zadnjeg dnevnika:", value=e_dnevnik if e_dnevnik else ""
            )
            u_oznaka = st.text_input(
                "Oznaka zemljišta:", value=e_oznaka if e_oznaka else ""
            )
            u_naziv = st.text_input(
                "Naziv zemljišta:", value=e_naziv if e_naziv else ""
            )
            u_nap = st.text_area(
                "Nova interna napomena:", value=e_nap if e_nap else ""
            )

            kategorije_sifre = [
                "— Bez šifre —",
                "Čestice na drugim posjedovnim listovima",
                "Usmeno dogovoreno (nije prepisano)",
                "Čestice na starim listovima",
            ]
            indeks_sifre = (
                kategorije_sifre.index(e_sifra)
                if e_sifra in kategorije_sifre
                else 0
            )
            u_sifra = st.selectbox(
                "Interna šifra / Kategorija čestice:",
                kategorije_sifre,
                index=indeks_sifre,
            )

            trenutno_p_naziv = p_obrnuti_dict.get(
                e_pod_id, list(p_dict.keys())[0]
            )
            popis_p = list(p_dict.keys())
            indeks_p = popis_p.index(trenutno_p_naziv)
            u_podrucje = st.selectbox(
                "Premjesti u područje:", popis_p, index=indeks_p
            )

            if st.form_submit_button("Spremi Izmjene Čestice"):
                try:
                    cursor.execute(
                        """
                        UPDATE cestice 
                        SET zk_ulozak=%s, broj_zadnjeg_dnevnika=%s, oznaka_zemljista=%s, naziv_zemljista=%s, napomena=%s, povrsina=%s, katastarska_opcina=%s, id_podrucja=%s, sifra=%s 
                        WHERE id=%s
                        """,
                        (
                            u_zk if u_zk else None,
                            u_dnevnik if u_dnevnik else None,
                            u_oznaka if u_oznaka else None,
                            u_naziv if u_naziv else None,
                            u_nap if u_nap else None,
                            u_pov if u_pov > 0 else None,
                            u_ko if u_ko else None,
                            p_dict[u_podrucje],
                            None if u_sifra == "— Bez šifre —" else u_sifra,
                            id_za_izmjenu,
                        ),
                    )
                    conn.commit()
                    st.success("Podaci o čestici uspješno ažurirani!")
                    st.rerun()
                except Exception as e:
                    if conn:
                        conn.rollback()
                    st.error(f"❌ Greška prilikom spremanja čestice: {e}")
    else:
        st.info("U bazi još nema čestica za uređivanje.")

    st.write("---")

    # =========================================================================
    # NOVI DIO 2: POPRAVAK I UREĐIVANJE UPISANIH STARIH LISTOVA/DOKUMENATA
    # =========================================================================
    st.subheader("📜 Izmjena i popravak povijesnih listova")

    # Povlačimo sve upisane dokumente iz baze na internetu
    cursor.execute(
        """
        SELECT pd.id, pd.vrsta_lista, pd.broj_lista_korisnika, c.broj_cestice 
        FROM povijest_dokumenata pd 
        JOIN cestice c ON pd.id_cestice = c.id
    """
    )
    svi_dokumenti_baza = cursor.fetchall()

    if svi_dokumenti_baza:
        # Radimo rječnik za padajući izbornik kako biste znali koji list popravljate
        d_uredi_dict = {
            f"{vrsta} br. {broj} (na čestici {br_c})": id_d
            for id_d, vrsta, broj, br_c in svi_dokumenti_baza
        }

        odabrana_doc_za_izmjenu = st.selectbox(
            "Odaberi povijesni list koji želiš popraviti:",
            list(d_uredi_dict.keys()),
            key="izbornik_za_izmjenu_dokumenata",
        )
        id_dokumenta_za_izmjenu = d_uredi_dict[odabrana_doc_za_izmjenu]

        # Učitavamo trenutne podatke tog dokumenta iz baze
        cursor.execute(
            """
            SELECT vrsta_lista, broj_lista_korisnika, starost_godina, upisani_vlasnik_posjednik, povijesna_napomena, datoteka 
            FROM povijest_dokumenata WHERE id = %s
        """,
            (id_dokumenta_za_izmjenu,),
        )
        d_vrsta, d_broj, d_starost, d_vlasnik, d_napomena, d_datoteka = (
            cursor.fetchone()
        )

        # Generiramo formu u kojoj vas ČEKAJU učitani stari podaci
        with st.form("forma_izmjene_dokumenata"):
            st.markdown(f"📄 Uređujete dokument: **{odabrana_doc_za_izmjenu}**")

            novi_d_vrsta = st.selectbox(
                "Vrsta dokumenta:",
                ["Posjedovni list", "Vlasnički list"],
                index=0 if d_vrsta == "Posjedovni list" else 1,
            )
            novi_d_broj = st.text_input("Broj lista / uložka:", value=d_broj if d_broj else "")
            novi_d_starost = st.text_input("Starost / Godina:", value=d_starost if d_starost else "")
            novi_d_vlasnik = st.text_input("Upisani vlasnik / posjednik:", value=d_vlasnik if d_vlasnik else "")
            novi_d_napomena = st.text_area("Povijesna napomena:", value=d_napomena if d_napomena else "")

            # OVDJE SADA MOŽETE DOPISATI .pdf EKSTENZIJU KOJA VAM NEDOSTAJE
            novi_d_datoteka = st.text_input(
                "Točan naziv datoteke u mapi (Ovdje nadopišite .pdf):",
                value=d_datoteka if d_datoteka else "",
            )

            if st.form_submit_button("Spremi Izmjene Dokumenta"):
                try:
                    cursor.execute(
                        """
                        UPDATE povijest_dokumenata 
                        SET vrsta_lista=%s, broj_lista_korisnika=%s, starost_godina=%s, upisani_vlasnik_posjednik=%s, povijesna_napomena=%s, datoteka=%s 
                        WHERE id=%s
                        """,
                        (
                            novi_d_vrsta,
                            novi_d_broj if novi_d_broj else None,
                            novi_d_starost if novi_d_starost else None,
                            novi_d_vlasnik if novi_d_vlasnik else None,
                            novi_d_napomena if novi_d_napomena else None,
                            novi_d_datoteka if novi_d_datoteka else None,
                            id_dokumenta_za_izmjenu,
                        ),
                    )
                    conn.commit()
                    st.success(
                        "Naziv datoteke i podaci dokumenta su uspješno popravljeni!"
                    )
                    st.rerun()
                except Exception as e:
                    if conn:
                        conn.rollback()
                    st.error(f"❌ Greška prilikom ažuriranja dokumenta: {e}")
    else:
        st.info("U bazi još nema unesenih dokumenata koje biste mogli uređivati.")
