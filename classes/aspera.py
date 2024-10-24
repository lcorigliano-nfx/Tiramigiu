import os
import platform
import subprocess
from classes.log import Log
import tempfile
from typing import Dict, List, Tuple

class Aspera:
    def __init__(self, batch_info: Dict, download_folder: str = "./dl/", movie_id: str = ""):
        self.batch_info = batch_info
        self.ascp_path = self.get_ascp_path()
        self.aspera_key_path = self.get_aspera_key_path()
        self.logger = Log().get_logger(self.__class__.__name__)
        self.download_folder = download_folder
        self.movie_id = movie_id
        
    def get_ascp_path(self) -> str:
        """Get the path to the ascp executable based on the operating system."""
        system = platform.system()
        if system == 'Darwin':  # macOS
            user_app_path = os.path.expanduser('~/Applications/Aspera Connect.app/Contents/Resources/ascp')
            if os.path.exists(user_app_path):
                return user_app_path
            return '/Applications/Aspera Connect.app/Contents/Resources/ascp'
        elif system == 'Windows':  # Windows
            return 'C:\\Program Files\\IBM\\Aspera Connect\\bin\\ascp.exe'
        elif system == 'Linux':  # Linux
            return os.path.expanduser('~/.aspera/connect/bin/ascp')
        else:
            raise OSError("Unsupported operating system")

    def get_aspera_key_path(self) -> str:
        """Get the path to the Aspera key file based on the operating system."""
        system = platform.system()
        if system == 'Darwin':  # macOS
            user_key_path = os.path.expanduser('~/Applications/Aspera Connect.app/Contents/Resources/asperaweb_id_dsa.openssh')
            if os.path.exists(user_key_path):
                return user_key_path
            return '/Applications/Aspera Connect.app/Contents/Resources/asperaweb_id_dsa.openssh'
        elif system == 'Windows':  # Windows
            return os.path.abspath('.\\asperakey.openssh')
        elif system == 'Linux':  # Linux
            return os.path.expanduser('~/.aspera/connect/etc/asperaweb_id_dsa.openssh')
        else:
            raise OSError("Unsupported operating system")

    def start_batch_download(self) -> None:
        """Start the batch download process using Aspera."""
        aspera_host = self.batch_info['asperaHost']
        aspera_transport_token = self.batch_info['asperaTransportToken']
        aspera_user = self.batch_info.get('asperaUser', 'filetransfer')

        if 'fileDownloads' not in self.batch_info or len(self.batch_info['fileDownloads']) == 0:
            self.logger.error("No files to download.")
            return

        # Create a list of source-destination pairs
        file_pairs: List[Tuple[str, str]] = []
        for file_info in self.batch_info['fileDownloads']:
            aspera_source = file_info['asperaSource']
            
            # Construct the destination path
            destination_filename = file_info['destinationPath'].strip('/')
            if self.movie_id:
                destination_filename = f"{self.movie_id}_{destination_filename}"
            destination_dir = os.path.abspath(os.path.join(self.download_folder, destination_filename))
            os.makedirs(os.path.dirname(destination_dir), exist_ok=True)
            
            # Add the source-destination pair to the list
            file_pairs.append((aspera_source, destination_filename))

        # Create a temporary file for the source-destination pairs
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as pair_list_file:
            for source, destination in file_pairs:
                self.logger.debug(f"Adding to queue: {destination}")
                pair_list_file.write(f"{source}\n{destination}\n")
            pair_list_filename = pair_list_file.name
        command = [
            self.ascp_path,
            "-i", self.aspera_key_path,
            "-W", aspera_transport_token,
            "--mode=recv",
            f"--host={aspera_host}",
            f"--user={aspera_user}",
            "--overwrite=diff",
            f"--file-pair-list={pair_list_filename}",
            self.download_folder.replace('\\', '/')
        ]

        try:
            self.logger.info("Starting batch download...")
            subprocess.run(command, check=True)
            self.logger.info("Batch download finished successfully.")
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Error during batch download: {e}")
        finally:
            # Remove the temporary file
            os.unlink(pair_list_filename)