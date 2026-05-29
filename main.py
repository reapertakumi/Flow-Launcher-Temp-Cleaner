import sys
import json
import os
import shutil
import ctypes

def show_msg(title, text):
    """Displays a native Windows message box without external dependencies."""
    # 0x40 represents MB_ICONINFORMATION
    ctypes.windll.user32.MessageBoxW(0, text, title, 0x40)

def get_paths(settings):
    """Extracts, splits, and expands paths from the Flow Launcher settings panel."""
    # Default fallback values matching your exact setup
    default_str = r"C:\Users\Alessio_Laptop\AppData\Local\Temp;C:\Windows\Temp;C:\Windows\Prefetch"
    
    raw_folders = settings.get("temp_folders", default_str).strip() if settings else default_str
    if not raw_folders:
        raw_folders = default_str
        
    # Split paths by semicolon and strip out extra spaces
    paths = [os.path.expandvars(p.strip()) for p in raw_folders.split(";") if p.strip()]
    return paths

def wipe_directory_contents(target_folders):
    """Safely erases files while tracking and skipping locked system items."""
    cleared_items = 0
    locked_items = 0
    for folder in target_folders:
        if not os.path.exists(folder):
            continue
        try:
            for element in os.listdir(folder):
                target_item = os.path.join(folder, element)
                try:
                    if os.path.isfile(target_item) or os.path.islink(target_item):
                        os.unlink(target_item)
                    elif os.path.isdir(target_item):
                        shutil.rmtree(target_item)
                    cleared_items += 1
                except Exception:
                    locked_items += 1
        except Exception:
            pass 
    return cleared_items, locked_items

def handle_query(query, settings):
    paths = get_paths(settings)
    results = []
    query = query.strip()

    # 1. Feature: Parse specific numeric index cleaning selections (e.g., '1,3' or '1,2,3')
    if query:
        indices_str = [p.strip() for p in query.split(",") if p.strip().isdigit()]
        if indices_str:
            selected_indices = [int(p) - 1 for p in indices_str]
            valid_paths = [paths[i] for i in selected_indices if 0 <= i < len(paths)]
            
            if valid_paths:
                return [{
                    "Title": f"Clean targeted slots: {', '.join(indices_str)}",
                    "SubTitle": f"Will wipe target folders: {', '.join([os.path.basename(p) or p for p in valid_paths])}",
                    "IcoPath": "Images/trash.png", # Deletion action gets the trash icon
                    "JsonRPCAction": {
                        "method": "clean_specific_paths",
                        "parameters": [selected_indices]
                    }
                }]

    # 2. Main Option: Clean All Folders (Assigned the Trash Icon)
    results.append({
        "Title": "Clean All Folders",
        "SubTitle": f"Purge every item inside all {len(paths)} configured pathways.",
        "IcoPath": "Images/trash.png", 
        "JsonRPCAction": {
            "method": "clean_all_paths",
            "parameters": []
        }
    })

    # 3. Individual Listed Folders (Assigned the Folder Icon)
    for i, path in enumerate(paths, start=1):
        results.append({
            "Title": f"[{i}] {path}",
            "SubTitle": "Select to clear this individual folder target.",
            "IcoPath": "Images/folder.png", 
            "JsonRPCAction": {
                "method": "clean_specific_paths",
                "parameters": [[i - 1]]
            }
        })

    return results

def main():
    if len(sys.argv) < 2:
        return
    
    try:
        # Native JSON-RPC communication API parsing
        request = json.loads(sys.argv[1])
        method = request.get("method")
        params = request.get("parameters", [])
        settings = request.get("settings", {})
        
        if method == "query":
            query_text = params[0] if params else ""
            results = handle_query(query_text, settings)
            print(json.dumps({"result": results}))
            
        elif method == "clean_all_paths":
            paths = get_paths(settings)
            cleared, locked = wipe_directory_contents(paths)
            msg = f"Purged {cleared} items."
            if locked:
                msg += f" Skipped {locked} active/locked files securely."
            show_msg("Cleanup Finished", msg)
            
        elif method == "clean_specific_paths":
            all_paths = get_paths(settings)
            indices = params[0]
            targets = [all_paths[i] for i in indices if 0 <= i < len(all_paths)]
            cleared, locked = wipe_directory_contents(targets)
            msg = f"Targeted directories cleared."
            if locked:
                msg += f" ({locked} locked elements left intact)"
            show_msg("Target Sweep Complete", msg)
            
    except Exception as e:
        import traceback
        # Fallback debug tracker inside the plugin directory if anything breaks native environments
        with open(os.path.join(os.path.dirname(__file__), "crash_log.txt"), "w") as f:
            f.write(traceback.format_exc())

if __name__ == "__main__":
    main()