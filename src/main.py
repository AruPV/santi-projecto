import csv
from enum import Enum
from typing import List, Tuple, Dict, Set
from datetime import datetime, timedelta
from collections import Counter

class DebugStats:
    def __init__(self):
        self.total_citi = 0
        self.total_sidera = 0
        self.matches = Counter()  # Counts by match type
        self.failed_matches = Counter()  # Counts reasons for failed matches
        self.camera_stats = {
            'citi': Counter(),
            'sidera': Counter(),
            'common': Counter()
        }
        
    def print_summary(self):
        print("\n=== ESTADÍSTICAS DE COINCIDENCIA ===")
        print(f"Total registros Citi: {self.total_citi}")
        print(f"Total registros Sidera: {self.total_sidera}")
        
        print("\nTipos de coincidencia:")
        for match_type, count in self.matches.items():
            print(f"  {match_type}: {count}")
        
        print("\nRazones de no coincidencia:")
        reason_translations = {
            'question_mark_camera': 'cámara con signo de interrogación',
            'camera_mismatch': 'cámara no coincide',
            'year_mismatch': 'año no coincide',
            'description_mismatch': 'descripción no coincide',
            'time_mismatch': 'hora fuera del rango permitido',
            'time_parse_error': 'error al procesar hora'
        }
        for reason, count in self.failed_matches.items():
            translated_reason = reason_translations.get(reason, reason)
            print(f"  {translated_reason}: {count}")
        
        print("\nEstadísticas de cámaras:")
        citi_cameras = set(self.camera_stats['citi'].keys())
        sidera_cameras = set(self.camera_stats['sidera'].keys())
        common_cameras = citi_cameras & sidera_cameras
        only_citi = citi_cameras - sidera_cameras
        only_sidera = sidera_cameras - citi_cameras
        
        print(f"  Cámaras únicas en Citi: {len(citi_cameras)}")
        print(f"  Cámaras únicas en Sidera: {len(sidera_cameras)}")
        print(f"  Cámaras en común: {len(common_cameras)}")
        
        print("\nCámaras solo en Citi:")
        for camera in sorted(only_citi):
            print(f"  {camera}: {self.camera_stats['citi'][camera]} registros")
            
        print("\nCámaras solo en Sidera:")
        for camera in sorted(only_sidera):
            print(f"  {camera}: {self.camera_stats['sidera'][camera]} registros")
        
        print("\nTop 5 cámaras por frecuencia:")
        print("  Citi:")
        for camera, count in self.camera_stats['citi'].most_common(5):
            print(f"    {camera}: {count} registros")
        print("  Sidera:")
        for camera, count in self.camera_stats['sidera'].most_common(5):
            print(f"    {camera}: {count} registros")

debug_stats = DebugStats()

def extract_time(time_str: str) -> str:
    """
    Extrae el tiempo en formato HH:MM de varios formatos de entrada:
    - HH:MM
    - HH:MM:SS
    - HH:MM:SS.SS
    """
    time_str = time_str.strip()
    
    # If time contains seconds or milliseconds, extract only HH:MM
    if ':' in time_str:
        parts = time_str.split(':')
        if len(parts) >= 2:
            return f"{parts[0].zfill(2)}:{parts[1].zfill(2)}"
    
    return time_str

def is_similar_time(time_str1: str, time_str2: str) -> bool:
    """
    Compara dos cadenas de tiempo y verifica si están dentro de un margen de 3 minutos.
    Maneja casos que cruzan la medianoche.
    """
    try:
        # Extract HH:MM format
        time1 = extract_time(time_str1)
        time2 = extract_time(time_str2)
        
        # Convert to datetime objects
        dt1 = datetime.strptime(time1, "%H:%M")
        dt2 = datetime.strptime(time2, "%H:%M")
        
        # Calculate difference
        diff = abs(dt1 - dt2)
        
        # Handle midnight crossing
        if diff > timedelta(hours=23):
            diff = timedelta(hours=24) - diff
        
        # Check if difference is <= 3 minutes
        return diff <= timedelta(minutes=3)
    except ValueError as e:
        print(f"Error comparing times: '{time_str1}' and '{time_str2}'")
        raise e

def clean_camera_id(s: str) -> str:
    """Clean camera ID by removing whitespace"""
    return s.strip()

def clean_description(s: str) -> str:
    """Clean description while preserving case and content"""
    return ' '.join(s.strip().split())

# Constants for empty rows in output
EMPTY_CITI = ["","","","","",""]
EMPTY_SIDERA = ["","","","","",""]

class MatchState(Enum):
    IDENTICAL = 1
    SIMILAR = 2
    DIFFERENT = 3

class Log:
    """
    Clase para manejar registros individuales de los archivos de log.
    Procesa y almacena datos de registros tanto de Citi como de Sidera.
    """
    def __init__(self, line: List, is_citi: bool):
        """
        Inicializa un registro de log.
        Args:
            line: Lista de campos del registro CSV
            is_citi: True si es un registro de Citi, False si es de Sidera
        """
        try:
            self.is_citi = is_citi
            self.raw = line
            self.camera_id = clean_camera_id(line[0])
            
            # Update camera statistics
            stats_key = 'citi' if is_citi else 'sidera'
            debug_stats.camera_stats[stats_key][self.camera_id] += 1
            
            if is_citi:
                self.desc = clean_description(line[3])
                self.year = line[4].strip()
                self.hour = line[5].strip()
            else:
                self.desc = clean_description(line[1])
                self.year = line[3].strip()
                self.hour = line[4].strip()
                self.seconds = line[5].strip() if len(line) > 5 else ""
        except IndexError as e:
            print(f"Error processing line: {line}")
            raise e

    def __str__(self):
        return f"{self.camera_id}_{self.year}_{self.hour}"

    def compare(self, other: 'Log', debug: bool = False) -> MatchState:
        """Compare this log with another log entry"""
        if debug:
            print(f"\nComparing logs:")
            print(f"Self:  {self.camera_id} | {self.desc} | {self.year} | {self.hour}")
            print(f"Other: {other.camera_id} | {other.desc} | {other.year} | {other.hour}")

        # If either log has '?' as camera_id, they don't match
        if self.camera_id == '?' or other.camera_id == '?':
            debug_stats.failed_matches['question_mark_camera'] += 1
            return MatchState.DIFFERENT

        # Check camera ID
        if self.camera_id != other.camera_id:
            debug_stats.failed_matches['camera_mismatch'] += 1
            return MatchState.DIFFERENT

        # Check year
        if self.year != other.year:
            debug_stats.failed_matches['year_mismatch'] += 1
            return MatchState.DIFFERENT

        # Check description
        if self.desc != other.desc:
            debug_stats.failed_matches['description_mismatch'] += 1
            return MatchState.DIFFERENT

        # Check time
        try:
            if self.hour == other.hour:
                return MatchState.IDENTICAL

            if is_similar_time(self.hour, other.hour):
                return MatchState.SIMILAR
            
            debug_stats.failed_matches['time_mismatch'] += 1
        except ValueError:
            debug_stats.failed_matches['time_parse_error'] += 1
            if debug:
                print(f"Time comparison failed for {self} and {other}")
            return MatchState.DIFFERENT
            
        return MatchState.DIFFERENT

class TrafficEvent:
    def __init__(self, log: Log):
        self.citi_logs: List[Log] = []
        self.sidera_logs: List[Log] = []
        if log.is_citi:
            self.citi_logs.append(log)
        else:
            self.sidera_logs.append(log)

    def add_if_same(self, log: Log) -> bool:
        """Try to add a log to this event if it matches. Returns True if added."""
        if log.is_citi:
            if not self.citi_logs:
                self.citi_logs.append(log)
                return True
            if any(existing.compare(log) != MatchState.DIFFERENT for existing in self.citi_logs):
                self.citi_logs.append(log)
                return True
        else:
            if not self.sidera_logs:
                self.sidera_logs.append(log)
                return True
            if any(existing.compare(log) != MatchState.DIFFERENT for existing in self.sidera_logs):
                self.sidera_logs.append(log)
                return True
        return False

    def title(self) -> str:
        """Determine match status and update statistics"""
        status = self._calculate_title()
        debug_stats.matches[status] += 1
        return status

    def _calculate_title(self) -> str:
        # No matches case
        if len(self.citi_logs) == 0 or len(self.sidera_logs) == 0:
            return "no coincide"

        # Single match case (1-to-1)
        if len(self.citi_logs) == 1 and len(self.sidera_logs) == 1:
            match_state = self.citi_logs[0].compare(self.sidera_logs[0])
            if match_state == MatchState.IDENTICAL:
                return "coincide"
            elif match_state == MatchState.SIMILAR:
                return "coincide diff horas"

        # Both have multiple logs
        if len(self.citi_logs) > 1 and len(self.sidera_logs) > 1:
            return "repetido ambos"

        # One side has multiple logs
        if len(self.citi_logs) > len(self.sidera_logs):
            return "repetido citi"
        elif len(self.citi_logs) < len(self.sidera_logs):
            return "repetido sidera"
        
        return "no coincide"

    def return_list(self) -> List:
        cached_title = self.title()
        max_length = max(len(self.citi_logs), len(self.sidera_logs))

        sidera_output = [log.raw for log in self.sidera_logs]
        citi_output = [log.raw for log in self.citi_logs]

        citi_padded = citi_output + [EMPTY_CITI] * (max_length - len(citi_output))
        sidera_padded = sidera_output + [EMPTY_SIDERA] * (max_length - len(sidera_output))

        return_list = []
        for citi_log, sidera_log in zip(citi_padded, sidera_padded):
            return_list.append(citi_log + sidera_log + [cached_title])

        return return_list

def are_logs_similar(log1: Log, log2: Log) -> bool:
    """Helper function to check if two logs are similar enough to be grouped"""
    return (log1.desc == log2.desc and
            log1.year == log2.year and
            is_similar_time(log1.hour, log2.hour))

def compare_files(citi_path: str, sidera_path: str, debug: bool = False):
    """
    Compara archivos de registro de Citi y Sidera, identificando coincidencias y diferencias.
    
    Args:
        citi_path: Ruta al archivo CSV de Citi
        sidera_path: Ruta al archivo CSV de Sidera
        debug: Si es True, muestra información detallada durante el proceso
    
    El proceso:
    1. Lee y procesa los archivos CSV
    2. Agrupa registros por cámara
    3. Encuentra coincidencias entre registros
    4. Maneja casos especiales (cámaras con '?', registros repetidos)
    5. Genera un archivo CSV con los resultados
    """
    print("Iniciando comparación...")
    debug_stats.__init__()  # Reiniciar estadísticas
    
    try:
        # Read input files
        with open(citi_path, encoding='iso-8859-1') as citi_raw:
            citi_log_file = list(csv.reader(citi_raw, delimiter=';'))
        
        with open(sidera_path, encoding='iso-8859-1') as sidera_raw:
            sidera_log_file = list(csv.reader(sidera_raw, delimiter=';'))

        # Update total counts
        debug_stats.total_citi = len(citi_log_file) - 1  # -1 for header
        debug_stats.total_sidera = len(sidera_log_file) - 1  # -1 for header

        if debug:
            print(f"Processing {debug_stats.total_citi} Citi logs and {debug_stats.total_sidera} Sidera logs")
            print("\nSample Citi logs:")
            for row in citi_log_file[1:4]:
                print(row)
            print("\nSample Sidera logs:")
            for row in sidera_log_file[1:4]:
                print(row)

        # Create Log objects (skip headers)
        citi_logs = [Log(line, True) for line in citi_log_file[1:]]
        sidera_logs = [Log(line, False) for line in sidera_log_file[1:]]
        events = []
        used_sidera = set()
        used_citi = set()

        # Group logs by camera ID
        citi_by_camera: Dict[str, List[Tuple[int, Log]]] = {}
        sidera_by_camera: Dict[str, List[Tuple[int, Log]]] = {}

        for idx, log in enumerate(citi_logs):
            if log.camera_id not in citi_by_camera:
                citi_by_camera[log.camera_id] = []
            citi_by_camera[log.camera_id].append((idx, log))

        for idx, log in enumerate(sidera_logs):
            if log.camera_id not in sidera_by_camera:
                sidera_by_camera[log.camera_id] = []
            sidera_by_camera[log.camera_id].append((idx, log))

        if debug:
            print("\nCamera grouping stats:")
            print(f"Unique camera IDs in Citi: {len(citi_by_camera)}")
            print(f"Unique camera IDs in Sidera: {len(sidera_by_camera)}")
            common_cameras = set(citi_by_camera.keys()) & set(sidera_by_camera.keys())
            print(f"Common camera IDs: {len(common_cameras)}")

        # Process each camera ID
        for camera_id in set(citi_by_camera.keys()) | set(sidera_by_camera.keys()):
            if camera_id == '?':  # Skip '?' camera IDs for special handling
                continue

            citi_group = citi_by_camera.get(camera_id, [])
            sidera_group = sidera_by_camera.get(camera_id, [])
            
            if debug and (len(citi_group) > 0 or len(sidera_group) > 0):
                print(f"\nProcessing camera {camera_id}:")
                print(f"  Citi logs: {len(citi_group)}")
                print(f"  Sidera logs: {len(sidera_group)}")
            
            # Group similar Citi logs first
            citi_subgroups = []
            used_citi_in_group = set()

            # Create subgroups of similar Citi logs
            for citi_idx, citi_log in citi_group:
                if citi_idx in used_citi_in_group:
                    continue
                
                current_group = [(citi_idx, citi_log)]
                used_citi_in_group.add(citi_idx)

                # Find similar Citi logs
                for other_idx, other_log in citi_group:
                    if other_idx not in used_citi_in_group:
                        if are_logs_similar(citi_log, other_log):
                            current_group.append((other_idx, other_log))
                            used_citi_in_group.add(other_idx)

                citi_subgroups.append(current_group)

            # Now process each Citi subgroup
            for citi_subgroup in citi_subgroups:
                # Get the first log as reference
                _, first_citi_log = citi_subgroup[0]
                event = TrafficEvent(first_citi_log)
                used_citi.add(citi_subgroup[0][0])
                
                # Add all other Citi logs from subgroup
                for citi_idx, citi_log in citi_subgroup[1:]:
                    event.add_if_same(citi_log)
                    used_citi.add(citi_idx)

                # Find matching Sidera logs
                matching_sideras = []
                matching_sidera_idxs = []

                for sidera_idx, sidera_log in sidera_group:
                    if sidera_idx in used_sidera:
                        continue
                    if first_citi_log.compare(sidera_log) != MatchState.DIFFERENT:
                        matching_sideras.append(sidera_log)
                        matching_sidera_idxs.append(sidera_idx)

                # Add matching Sidera logs
                for sidera_log, sidera_idx in zip(matching_sideras, matching_sidera_idxs):
                    event.add_if_same(sidera_log)
                    used_sidera.add(sidera_idx)

                events.append(event)

        # Handle remaining Sidera logs
        for camera_id, sidera_group in sidera_by_camera.items():
            # Group similar Sidera logs
            current_group = []
            for sidera_idx, sidera_log in sidera_group:
                if sidera_idx not in used_sidera:
                    if not current_group or are_logs_similar(current_group[0][1], sidera_log):
                        current_group.append((sidera_idx, sidera_log))
                        used_sidera.add(sidera_idx)
                    else:
                        if current_group:
                            event = TrafficEvent(current_group[0][1])
                            for _, log in current_group[1:]:
                                event.add_if_same(log)
                            events.append(event)
                            current_group = [(sidera_idx, sidera_log)]
                            used_sidera.add(sidera_idx)
            
            if current_group:
                event = TrafficEvent(current_group[0][1])
                for _, log in current_group[1:]:
                    event.add_if_same(log)
                events.append(event)

        # Finally handle remaining Citi logs with '?' camera_id
        question_mark_groups = []
        remaining_citi = [(idx, log) for idx, log in enumerate(citi_logs) 
                         if log.camera_id == '?' and idx not in used_citi]
        
        if debug and remaining_citi:
            print(f"\nProcessing {len(remaining_citi)} remaining Citi logs with '?' camera_id")
        
        for citi_idx, citi_log in remaining_citi:
            found_group = False
            for group in question_mark_groups:
                if are_logs_similar(group[0][1], citi_log):
                    group.append((citi_idx, citi_log))
                    found_group = True
                    break
            if not found_group:
                question_mark_groups.append([(citi_idx, citi_log)])

        for group in question_mark_groups:
            event = TrafficEvent(group[0][1])
            for _, log in group[1:]:
                event.add_if_same(log)
            events.append(event)

        # Prepare output
        return_list = []
        return_list.append(["CITILOG","","","","","","SIDERA","","","","",""])
        return_list.append([
            "CameraName","Start","IncType","IncType","TEXTO AÑOS","TEXTO HORAS",
            "Equipo","Desc. variable","Fecha","TEXTO AÑOS","TEXTO HORAS","TEXTO SEGUNDOS","ESTADO"
        ])
        
        for event in events:
            return_list.extend(event.return_list())

        # Print statistics
        debug_stats.print_summary()

        print("\nWriting output.csv...")
        with open("output.csv", 'w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerows(return_list)
            
        print("Comparison completed successfully!")
        
    except Exception as e:
        print(f"Error during comparison: {e}")
        raise e

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Compare Citi and Sidera log files')
    parser.add_argument('citi_path', help='Path to Citi log file')
    parser.add_argument('sidera_path', help='Path to Sidera log file')
    parser.add_argument('--debug', action='store_true', help='Enable debug output')
    parser.add_argument('--output', default='output.csv', help='Output file path (default: output.csv)')
    args = parser.parse_args()
    
    compare_files(args.citi_path, args.sidera_path, args.debug)
