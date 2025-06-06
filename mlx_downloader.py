#!/usr/bin/env python3
"""
MLX Model Downloader
Downloads and verifies MLX models from Hugging Face
"""

import sys
import shutil
from pathlib import Path
from huggingface_hub import snapshot_download
from mlx_lm import load

def download_model(model_name, verify=True, force_redownload=False):
    """Download and optionally verify an MLX model"""
    
    # Check current status
    status, model_path, incomplete_files = get_model_status(model_name)
    
    if status == "complete" and not force_redownload:
        print(f"✅ Model {model_name} already downloaded and complete")
        if verify:
            print("🔍 Verifying model loads correctly...")
            try:
                model, tokenizer = load(model_name)
                print(f"✅ Model verified: {model_name}")
                
                # Clean up memory
                del model, tokenizer
                import gc
                gc.collect()
                return True
            except Exception as e:
                print(f"❌ Model verification failed: {e}")
                print(f"🔄 Re-downloading due to verification failure...")
        else:
            return True
    
    if status == "incomplete":
        print(f"⚠️  Found incomplete download with {len(incomplete_files)} partial files")
        clean_incomplete_model(model_name)
    
    print(f"🔄 Downloading: {model_name}")
    
    try:
        # Download model files
        local_path = snapshot_download(
            repo_id=model_name,
            local_files_only=False,
            resume_download=True,
            force_download=force_redownload
        )
        print(f"✅ Downloaded to: {local_path}")
        
        # Verify final status
        final_status, _, _ = get_model_status(model_name)
        if final_status != "complete":
            print(f"⚠️  Download may be incomplete (status: {final_status})")
        
        if verify:
            print("🔍 Verifying model loads correctly...")
            try:
                model, tokenizer = load(model_name)
                print(f"✅ Model verified: {model_name}")
                
                # Clean up memory
                del model, tokenizer
                import gc
                gc.collect()
                
            except Exception as e:
                print(f"❌ Model verification failed: {e}")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ Download failed: {e}")
        return False


def get_cache_path():
    """Get Hugging Face cache directory"""
    return Path.home() / ".cache" / "huggingface" / "hub"

def get_model_status(model_name):
    """Check if model is downloaded and its status"""
    cache_path = get_cache_path()
    model_dir_name = f"models--{model_name.replace('/', '--')}"
    model_path = cache_path / model_dir_name
    
    if not model_path.exists():
        return "not_downloaded", None, []
    
    blobs_path = model_path / "blobs"
    if not blobs_path.exists():
        return "no_blobs", model_path, []
    
    # Check for incomplete files
    incomplete_files = list(blobs_path.glob("*.incomplete"))
    all_files = list(blobs_path.glob("*"))
    
    if incomplete_files:
        return "incomplete", model_path, incomplete_files
    
    # Check if snapshots exist
    snapshots_path = model_path / "snapshots"
    if snapshots_path.exists() and list(snapshots_path.glob("*")):
        return "complete", model_path, all_files
    
    return "unknown", model_path, all_files

def clean_incomplete_model(model_name):
    """Clean incomplete downloads for a model"""
    status, _, files = get_model_status(model_name)
    incomplete_files = files if status == "incomplete" else []
    
    if status == "incomplete":
        print(f"🧹 Cleaning {len(incomplete_files)} incomplete files for {model_name}")
        for file_path in incomplete_files:
            try:
                file_path.unlink()
                print(f"   Removed: {file_path.name}")
            except Exception as e:
                print(f"   ❌ Failed to remove {file_path.name}: {e}")
        return True
    elif status == "not_downloaded":
        print(f"ℹ️  Model {model_name} not downloaded yet")
        return False
    else:
        print(f"✅ Model {model_name} appears complete")
        return False

def remove_model(model_name):
    """Completely remove a model from cache"""
    status, model_path, _ = get_model_status(model_name)
    
    if status == "not_downloaded":
        print(f"ℹ️  Model {model_name} not found in cache")
        return False
    
    try:
        shutil.rmtree(model_path)
        print(f"🗑️  Completely removed {model_name} from cache")
        return True
    except Exception as e:
        print(f"❌ Failed to remove {model_name}: {e}")
        return False

def discover_local_models():
    """Discover all downloaded models in cache directory"""
    cache_path = get_cache_path()
    models = []
    
    if not cache_path.exists():
        return models
    
    # Look for model directories (format: models--org--model)
    for model_dir in cache_path.glob("models--*"):
        if model_dir.is_dir():
            # Convert directory name back to model name format
            # "models--mlx-community--Llama-3.2-3B-Instruct-4bit" -> "mlx-community/Llama-3.2-3B-Instruct-4bit"
            dir_name = model_dir.name
            if dir_name.startswith("models--"):
                model_name = dir_name[8:]  # Remove "models--" prefix
                # Split on "--" and rejoin properly: org/model-name-parts
                parts = model_name.split("--")
                if len(parts) >= 2:
                    # First part is organization, rest is model name with dashes
                    org = parts[0]
                    model_parts = parts[1:]
                    model_name = f"{org}/{'-'.join(model_parts)}"
                    models.append(model_name)
    
    return sorted(models)

def list_mlx_models():
    """Show all downloaded MLX models with status"""
    
    models = discover_local_models()
    
    if not models:
        print("📋 No MLX models found in cache directory")
        print(f"   Cache path: {get_cache_path()}")
        return models
    
    print(f"📋 Downloaded MLX Models ({len(models)} found):")
    for i, model in enumerate(models, 1):
        status, _, files = get_model_status(model)
        incomplete_files = files if status == "incomplete" else []
        status_emoji = {
            "complete": "✅",
            "incomplete": "⚠️ ",
            "not_downloaded": "⬜",
            "no_blobs": "❓",
            "unknown": "❓"
        }
        
        status_text = {
            "complete": "Complete",
            "incomplete": f"Incomplete ({len(incomplete_files)} partial files)",
            "not_downloaded": "Not downloaded",
            "no_blobs": "No blobs",
            "unknown": "Unknown status"
        }
        
        print(f"  {i:2d}. {status_emoji[status]} {model} - {status_text[status]}")
    
    return models


def main():
    if len(sys.argv) < 2:
        print("Enhanced MLX Model Downloader")
        print("Usage:")
        print("  python3 mlx_downloader.py <model_name>        # Download specific model")
        print("  python3 mlx_downloader.py list                # List downloaded models with status")
        print("  python3 mlx_downloader.py download <num>      # Download by number from list")
        print("  python3 mlx_downloader.py status <model|num>  # Check model status")
        print("  python3 mlx_downloader.py clean <model|num>   # Clean incomplete files")
        print("  python3 mlx_downloader.py remove <model|num>  # Remove model completely")
        print("  python3 mlx_downloader.py clean-all           # Clean all incomplete files")
        print("")
        list_mlx_models()
        return
    
    command = sys.argv[1]
    
    if command == "list":
        list_mlx_models()
        
    elif command == "download" and len(sys.argv) == 3:
        try:
            models = discover_local_models()
            if not models:
                print("❌ No models found in cache directory. Use direct model name to download new models.")
                return
            
            index = int(sys.argv[2]) - 1
            if 0 <= index < len(models):
                model_name = models[index]
                # Clean incomplete files first
                clean_incomplete_model(model_name)
                download_model(model_name)
            else:
                print(f"❌ Invalid number. Choose 1-{len(models)}")
        except ValueError:
            print("❌ Please provide a valid number")
    
    elif command == "status" and len(sys.argv) == 3:
        model_arg = sys.argv[2]
        
        # Check if it's a number (index) or model name
        try:
            index = int(model_arg) - 1
            models = discover_local_models()
            if not models:
                print("❌ No models found in cache directory")
                return
            
            if 0 <= index < len(models):
                model_name = models[index]
            else:
                print(f"❌ Invalid number. Choose 1-{len(models)}")
                return
        except ValueError:
            # Not a number, treat as model name
            model_name = model_arg
        
        status, model_path, files = get_model_status(model_name)
        print(f"📊 Status for {model_name}: {status}")
        if model_path:
            print(f"   Path: {model_path}")
        if files:
            print(f"   Files: {len(files)} files")
            if status == "incomplete":
                print(f"   Incomplete files: {[f.name for f in files]}")
    
    elif command == "clean" and len(sys.argv) == 3:
        model_arg = sys.argv[2]
        
        # Check if it's a number (index) or model name
        try:
            index = int(model_arg) - 1
            models = discover_local_models()
            if not models:
                print("❌ No models found in cache directory")
                return
            
            if 0 <= index < len(models):
                model_name = models[index]
                clean_incomplete_model(model_name)
            else:
                print(f"❌ Invalid number. Choose 1-{len(models)}")
        except ValueError:
            # Not a number, treat as model name
            model_name = model_arg
            clean_incomplete_model(model_name)
    
    elif command == "remove" and len(sys.argv) == 3:
        model_arg = sys.argv[2]
        
        # Check if it's a number (index) or model name
        try:
            index = int(model_arg) - 1
            models = discover_local_models()
            if not models:
                print("❌ No models found in cache directory")
                return
            
            if 0 <= index < len(models):
                model_name = models[index]
            else:
                print(f"❌ Invalid number. Choose 1-{len(models)}")
                return
        except ValueError:
            # Not a number, treat as model name
            model_name = model_arg
        
        confirm = input(f"⚠️  Are you sure you want to completely remove {model_name}? (y/N): ")
        if confirm.lower() == 'y':
            remove_model(model_name)
        else:
            print("❌ Cancelled")
    
    elif command == "clean-all":
        models = discover_local_models()
        if not models:
            print("❌ No models found in cache directory")
            return
        
        cleaned_count = 0
        for model in models:
            if clean_incomplete_model(model):
                cleaned_count += 1
        print(f"🧹 Cleaned incomplete files for {cleaned_count} models")
            
    else:
        # Direct model name
        model_name = sys.argv[1]
        # Clean incomplete files first
        clean_incomplete_model(model_name)
        download_model(model_name)


if __name__ == "__main__":
    main()