#!/usr/bin/env python3
import os
import re
import shutil

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def apply_config():
    print(f"[ZenyDesk] Configuring ZenyDesk sovereign branding and servers in {REPO_ROOT}...")

    # 1. Update libs/hbb_common/src/config.rs
    config_path = os.path.join(REPO_ROOT, 'libs', 'hbb_common', 'src', 'config.rs')
    if os.path.isfile(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Update APP_NAME
        content = re.sub(
            r'pub static ref APP_NAME: RwLock<String> = RwLock::new\("[^"]*"\.to_owned\(\)\);',
            'pub static ref APP_NAME: RwLock<String> = RwLock::new("ZenyDesk".to_owned());',
            content
        )

        # Update BUILTIN_SETTINGS
        builtin_replacement = """    pub static ref BUILTIN_SETTINGS: RwLock<HashMap<String, String>> = RwLock::new({
        let mut m = HashMap::new();
        m.insert("api-server".to_string(), "https://zenydesk.com".to_string());
        m
    });"""
        content = re.sub(
            r'(?m)^\s*pub static ref BUILTIN_SETTINGS: RwLock<HashMap<String, String>> = (Default::default\(\)|RwLock::new\(\{[\s\S]*?\n\s*\}\));',
            builtin_replacement,
            content
        )

        # Update RENDEZVOUS_SERVERS
        content = re.sub(
            r'pub const RENDEZVOUS_SERVERS: &\[&str\] = &\[[^\]]*\];',
            'pub const RENDEZVOUS_SERVERS: &[&str] = &["zenydesk.com"];',
            content
        )

        # Update RS_PUB_KEY
        content = re.sub(
            r'pub const RS_PUB_KEY: &str = "[^"]*";',
            'pub const RS_PUB_KEY: &str = "AUDVAlSeBDEeu4WOGF1a05C6cXh14ZVxi4RP6L2knVQ=";',
            content
        )

        # Update LINK_DOCS_HOME
        content = re.sub(
            r'pub const LINK_DOCS_HOME: &str = "[^"]*";',
            'pub const LINK_DOCS_HOME: &str = "https://zenydesk.com";',
            content
        )

        # Update LINK_DOCS_X11_REQUIRED
        content = re.sub(
            r'pub const LINK_DOCS_X11_REQUIRED: &str = "[^"]*";',
            'pub const LINK_DOCS_X11_REQUIRED: &str = "https://zenydesk.com/suporte";',
            content
        )

        with open(config_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print("  -> libs/hbb_common/src/config.rs configured with ZenyDesk rendezvous server and pubkey.")
    else:
        print("  -> WARNING: libs/hbb_common/src/config.rs not found!")

    # 2. Update libs/hbb_common/src/lib.rs version check URL
    lib_path = os.path.join(REPO_ROOT, 'libs', 'hbb_common', 'src', 'lib.rs')
    if os.path.isfile(lib_path):
        with open(lib_path, 'r', encoding='utf-8') as f:
            lib_content = f.read()
        lib_content = lib_content.replace('https://api.rustdesk.com/version/latest', 'https://zenydesk.com/api/version/latest')
        with open(lib_path, 'w', encoding='utf-8') as f:
            f.write(lib_content)
        print("  -> libs/hbb_common/src/lib.rs version check URL updated to zenydesk.com.")

    # 3. Update src/common.rs default api-server fallback
    common_path = os.path.join(REPO_ROOT, 'src', 'common.rs')
    if os.path.isfile(common_path):
        with open(common_path, 'r', encoding='utf-8') as f:
            common_content = f.read()
        common_content = common_content.replace('"https://admin.rustdesk.com".to_owned()', '"https://zenydesk.com".to_owned()')
        with open(common_path, 'w', encoding='utf-8') as f:
            f.write(common_content)
        print("  -> src/common.rs default api-server fallback updated to zenydesk.com.")

    # 4. Update Cargo.lock package name if needed
    lock_path = os.path.join(REPO_ROOT, 'Cargo.lock')
    if os.path.isfile(lock_path):
        with open(lock_path, 'r', encoding='utf-8') as f:
            lock_content = f.read()
        if 'name = "rustdesk"\nversion = "1.4.9"' in lock_content:
            lock_content = lock_content.replace('name = "rustdesk"\nversion = "1.4.9"', 'name = "zenydesk"\nversion = "1.4.9"')
            with open(lock_path, 'w', encoding='utf-8') as f:
                f.write(lock_content)
            print("  -> Cargo.lock package name updated to 'zenydesk'.")

    # 5. Update libs/portable/Cargo.toml (Standalone Executable Winres metadata)
    portable_toml = os.path.join(REPO_ROOT, 'libs', 'portable', 'Cargo.toml')
    if os.path.isfile(portable_toml):
        with open(portable_toml, 'r', encoding='utf-8') as f:
            pt_content = f.read()
        pt_content = re.sub(r'name = "rustdesk-portable-packer"', 'name = "zenydesk-portable-packer"', pt_content)
        pt_content = re.sub(r'description = "RustDesk Remote Desktop"', 'description = "ZenyDesk Remote Desktop"', pt_content)
        pt_content = re.sub(r'ProductName = "RustDesk"', 'ProductName = "ZenyDesk"', pt_content)
        pt_content = re.sub(r'OriginalFilename = "rustdesk\.exe"', 'OriginalFilename = "zenydesk.exe"', pt_content)
        pt_content = re.sub(r'FileDescription = "RustDesk Remote Desktop"', 'FileDescription = "ZenyDesk Remote Desktop"', pt_content)
        pt_content = re.sub(r'LegalCopyright = "[^"]*"', 'LegalCopyright = "Copyright © 2026 CERTIMIX (CHL COMPANHIA DIGITAL LTDA). Todos os direitos reservados."', pt_content)
        with open(portable_toml, 'w', encoding='utf-8') as f:
            f.write(pt_content)
        print("  -> libs/portable/Cargo.toml winres metadata configured for ZenyDesk.")

    # 6. Update libs/portable/src/main.rs (Extraction directory & environment)
    portable_main = os.path.join(REPO_ROOT, 'libs', 'portable', 'src', 'main.rs')
    if os.path.isfile(portable_main):
        with open(portable_main, 'r', encoding='utf-8') as f:
            pm_content = f.read()
        pm_content = re.sub(r'const APP_PREFIX: &str = "rustdesk";', 'const APP_PREFIX: &str = "zenydesk";', pm_content)
        pm_content = re.sub(r'const APPNAME_RUNTIME_ENV_KEY: &str = "RUSTDESK_APPNAME";', 'const APPNAME_RUNTIME_ENV_KEY: &str = "ZENYDESK_APPNAME";', pm_content)
        with open(portable_main, 'w', encoding='utf-8') as f:
            f.write(pm_content)
        print("  -> libs/portable/src/main.rs extraction prefix set to 'zenydesk'.")

    # 7. Update libs/portable/src/bin_reader.rs (Magic identifier support)
    bin_reader = os.path.join(REPO_ROOT, 'libs', 'portable', 'src', 'bin_reader.rs')
    if os.path.isfile(bin_reader):
        with open(bin_reader, 'r', encoding='utf-8') as f:
            br_content = f.read()
        br_content = re.sub(
            r'if iden != "rustdesk" \{',
            'if iden != "zenydesk" && iden != "rustdesk" {',
            br_content
        )
        br_content = re.sub(
            r'if iden == "rustdesk" \{',
            'if iden == "zenydesk" || iden == "rustdesk" {',
            br_content
        )
        with open(bin_reader, 'w', encoding='utf-8') as f:
            f.write(br_content)
        print("  -> libs/portable/src/bin_reader.rs magic identifier updated.")

    # 8. Update libs/portable/generate.py
    generate_py = os.path.join(REPO_ROOT, 'libs', 'portable', 'generate.py')
    if os.path.isfile(generate_py):
        with open(generate_py, 'r', encoding='utf-8') as f:
            gen_content = f.read()
        gen_content = gen_content.replace('f.write("rustdesk".encode(encoding=encoding))', 'f.write("zenydesk".encode(encoding=encoding))')
        with open(generate_py, 'w', encoding='utf-8') as f:
            f.write(gen_content)
        print("  -> libs/portable/generate.py packer updated.")

    # 9. Update flutter/windows/CMakeLists.txt
    cmake_path = os.path.join(REPO_ROOT, 'flutter', 'windows', 'CMakeLists.txt')
    if os.path.isfile(cmake_path):
        with open(cmake_path, 'r', encoding='utf-8') as f:
            cm_content = f.read()
        cm_content = re.sub(r'set\(BINARY_NAME "rustdesk"\)', 'set(BINARY_NAME "zenydesk")', cm_content)
        cm_content = re.sub(r'project\(rustdesk LANGUAGES CXX\)', 'project(zenydesk LANGUAGES CXX)', cm_content)
        with open(cmake_path, 'w', encoding='utf-8') as f:
            f.write(cm_content)
        print("  -> flutter/windows/CMakeLists.txt BINARY_NAME updated to 'zenydesk'.")

    # 10. Update Android application config
    gradle_path = os.path.join(REPO_ROOT, 'flutter', 'android', 'app', 'build.gradle')
    if os.path.isfile(gradle_path):
        with open(gradle_path, 'r', encoding='utf-8') as f:
            gradle_content = f.read()
        gradle_content = re.sub(r'applicationId "[^"]*"', 'applicationId "com.zenydesk.client"', gradle_content)
        with open(gradle_path, 'w', encoding='utf-8') as f:
            f.write(gradle_content)
        print("  -> flutter/android/app/build.gradle applicationId set to 'com.zenydesk.client'.")

    strings_xml = os.path.join(REPO_ROOT, 'flutter', 'android', 'app', 'src', 'main', 'res', 'values', 'strings.xml')
    if os.path.isfile(strings_xml):
        with open(strings_xml, 'r', encoding='utf-8') as f:
            s_content = f.read()
        s_content = re.sub(r'<string name="app_name">[^<]*</string>', '<string name="app_name">ZenyDesk</string>', s_content)
        with open(strings_xml, 'w', encoding='utf-8') as f:
            f.write(s_content)
        print("  -> Android strings.xml app_name set to 'ZenyDesk'.")

    # 11. Ensure Icons are synced to runner directories
    icon_src = os.path.join(REPO_ROOT, 'res', 'icon.ico')
    win_icon_dest = os.path.join(REPO_ROOT, 'flutter', 'windows', 'runner', 'resources', 'app_icon.ico')
    if os.path.isfile(icon_src) and os.path.isdir(os.path.dirname(win_icon_dest)):
        shutil.copyfile(icon_src, win_icon_dest)
        print("  -> Synchronized app_icon.ico to flutter/windows/runner/resources/app_icon.ico.")

    print("[ZenyDesk] All sovereign configurations applied successfully!")

if __name__ == '__main__':
    apply_config()
