import ftplib
import io
import zipfile

def main():
    try:
        ftp = ftplib.FTP("ftp.mtps.gov.br")
        ftp.login()
        ftp.cwd("portal/fiscalizacao/seguranca-e-saude-no-trabalho/caepi")
        
        bio = io.BytesIO()
        ftp.retrbinary("RETR tgg_export_caepi.zip", bio.write)
        bio.seek(0)
        with zipfile.ZipFile(bio) as z:
            namelist = z.namelist()
            first_file = namelist[0]
            with z.open(first_file) as f:
                print("Counting lines...")
                line_count = 0
                for line in f:
                    line_count += 1
                print(f"Total lines: {line_count}")
        ftp.quit()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
