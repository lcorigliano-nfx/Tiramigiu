import os
import platform
import subprocess
from classes.log import Log
import tempfile
class Aspera:
    def __init__(self, batch_info):
        self.batch_info = batch_info
        self.ascp_path = self.get_ascp_path()
        self.aspera_key_path = self.get_aspera_key_path()
        self.logger = Log().logger
        self.download_folder = "./dl/"

    def get_ascp_path(self):
        system = platform.system()
        if system == 'Darwin':  # macOS
            user_app_path = os.path.expanduser('~/Applications/Aspera Connect.app/Contents/Resources/ascp')
            if os.path.exists(user_app_path):
                return user_app_path
            return '/Applications/Aspera Connect.app/Contents/Resources/ascp'
        elif system == 'Windows':  # Windows
            return r'C:\Program Files (x86)\Aspera\Aspera Connect\bin\ascp.exe'
        elif system == 'Linux':  # Linux
            return os.path.expanduser('~/.aspera/connect/bin/ascp')
        else:
            raise OSError("Unsupported operating system")

    def get_aspera_key_path(self):
        system = platform.system()
        if system == 'Darwin':  # macOS
            user_key_path = os.path.expanduser('~/Applications/Aspera Connect.app/Contents/Resources/asperaweb_id_dsa.openssh')
            if os.path.exists(user_key_path):
                return user_key_path
            return '/Applications/Aspera Connect.app/Contents/Resources/asperaweb_id_dsa.openssh'
        elif system == 'Windows':  # Windows
            return r'C:\Program Files (x86)\Aspera\Aspera Connect\etc\asperaweb_id_dsa.openssh'
        elif system == 'Linux':  # Linux
            return os.path.expanduser('~/.aspera/connect/etc/asperaweb_id_dsa.openssh')
        else:
            raise OSError("Unsupported operating system")



    def start_batch_download(self):
        aspera_host = self.batch_info['asperaHost']
        aspera_transport_token = self.batch_info['asperaTransportToken']
        aspera_user = self.batch_info.get('asperaUser', 'filetransfer')

        if 'fileDownloads' not in self.batch_info or len(self.batch_info['fileDownloads']) == 0:
            self.logger.error("No files to download.")
            return

        # Creare una lista delle sorgenti e delle destinazioni
        file_pairs = []
        for file_info in self.batch_info['fileDownloads']:
            aspera_source = file_info['asperaSource']
            
            # Costruire il percorso di destinazione
            destination_filename = file_info['destinationPath'].strip('/')
            destination_dir = os.path.abspath(os.path.join(self.download_folder, destination_filename))
            os.makedirs(os.path.dirname(destination_dir), exist_ok=True)
            
            # Aggiungere la coppia sorgente-destinazione alla lista
            file_pairs.append((aspera_source, destination_filename))

        # Creare un file temporaneo per le coppie sorgente-destinazione
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as pair_list_file:
            for source, destination in file_pairs:
                pair_list_file.write(f"{source}\n{destination}\n")
            pair_list_filename = pair_list_file.name
        with open(pair_list_filename, 'r') as f:
            print(f.read()) # Debug

        command = [
            self.ascp_path,
            "-i", self.aspera_key_path,
            "-W", aspera_transport_token,
            "--mode=recv",
            f"--host={aspera_host}",
            f"--user={aspera_user}",
            "--overwrite=diff",
            f"--file-pair-list={pair_list_filename}",
            self.download_folder
        ]

        try:
            subprocess.run(command, check=True)
            self.logger.info("Batch download started successfully.")
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Error during batch download: {e}")
        finally:
            # Rimuovere il file temporaneo
            os.unlink(pair_list_filename)

