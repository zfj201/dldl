package com.zfj.dldlextension;

import java.io.*;
import java.nio.file.Files;
import java.nio.file.StandardCopyOption;
import java.security.MessageDigest;
import java.util.zip.ZipFile;
import org.json.JSONObject;

/** 从已安装模块 APK 取出扩展；SHA-256 检查完整性，来源信任依赖模块 APK 的签名。 */
final class PayloadStore {
    static String digest(byte[] data) throws Exception {
        StringBuilder out = new StringBuilder();
        for (byte b : MessageDigest.getInstance("SHA-256").digest(data)) out.append(String.format("%02x", b & 255));
        return out.toString();
    }
    private static byte[] entry(ZipFile zip, String name) throws Exception {
        java.util.zip.ZipEntry e = zip.getEntry(name);
        if (e == null || e.getSize() > 2_000_000) throw new IOException("Missing/oversized module resource: " + name);
        try (InputStream in = zip.getInputStream(e); ByteArrayOutputStream out = new ByteArrayOutputStream()) {
            byte[] b = new byte[8192]; int n;
            while ((n = in.read(b)) != -1) {
                out.write(b, 0, n);
                if (out.size() > 2_000_000) throw new IOException("Resource size limit");
            }
            return out.toByteArray();
        }
    }
    static File prepare(String apk, File base) throws Exception {
        // apk 是模块的 sourceDir，不是游戏 APK；发布内容没有在线下载入口。
        try (ZipFile zip = new ZipFile(apk)) {
            byte[] manifest = entry(zip, "assets/extension/manifest.json");
            JSONObject files = new JSONObject(new String(manifest, java.nio.charset.StandardCharsets.UTF_8)).getJSONObject("files");
            // 目录随扩展内容变化；不绑定某个官方 game_start 哈希或游戏版本。
            File directory = new File(base, "bundle-" + digest(manifest).substring(0, 16));
            if (!directory.isDirectory() && !directory.mkdirs()) throw new IOException("Cannot create payload directory");
            for (String name : new String[]{"bootstrap.lua", "payload.lua", "startup.lua", "splash.lua"}) {
                byte[] bytes = entry(zip, "assets/extension/" + name);
                if (!digest(bytes).equals(files.getString(name))) throw new IOException("APK payload hash mismatch: " + name);
                File destination = new File(directory, name);
                // 冷启动复用完整副本；文件丢失或损坏则从模块 APK 恢复。
                if (destination.isFile() && digest(Files.readAllBytes(destination.toPath())).equals(files.getString(name))) continue;
                File temp = new File(directory, name + ".tmp");
                try (FileOutputStream out = new FileOutputStream(temp)) { out.write(bytes); out.getFD().sync(); }
                // 先写完临时文件再原子替换，避免加载到只写了一半的 Lua。
                Files.move(temp.toPath(), destination.toPath(), StandardCopyOption.ATOMIC_MOVE, StandardCopyOption.REPLACE_EXISTING);
            }
            return new File(directory, "bootstrap.lua");
        }
    }
    static void verifyNative(String apk) throws Exception {
        try (ZipFile zip = new ZipFile(apk)) {
            String expected = new String(entry(zip, "assets/extension/native.sha256"), java.nio.charset.StandardCharsets.US_ASCII).trim();
            if (!digest(entry(zip, "lib/arm64-v8a/libdldl_bridge.so")).equals(expected)) throw new IOException("Native resource hash mismatch");
        }
    }
    private PayloadStore() {}
}
