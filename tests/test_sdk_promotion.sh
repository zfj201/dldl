#!/bin/sh
set -eu
ROOT=$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)
TASK_TMP=$(mktemp -d)
trap 'rm -rf "$TASK_TMP"' EXIT
mkdir -p "$TASK_TMP/io/github/libxposed/api" "$TASK_TMP/com/zfj/dldlextension"
# Minimal API surface for an isolated JVM contract test; APK compilation uses the real API.
cat > "$TASK_TMP/io/github/libxposed/api/XposedInterface.java" <<'JAVA'
package io.github.libxposed.api;
public interface XposedInterface {
    interface Chain { Object proceed() throws Throwable; }
    interface Hooker { Object intercept(Chain chain) throws Throwable; }
}
JAVA
cp "$ROOT/lsposed-module/app/src/main/java/com/zfj/dldlextension/SdkPromotionHook.java" "$TASK_TMP/com/zfj/dldlextension/"
cat > "$TASK_TMP/com/zfj/dldlextension/SdkPromotionTest.java" <<'JAVA'
package com.zfj.dldlextension;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.atomic.AtomicBoolean;
import io.github.libxposed.api.XposedInterface;

public final class SdkPromotionTest {
    static void check(boolean ok, String message) { if (!ok) throw new AssertionError(message); }
    public static void main(String[] args) throws Throwable {
        AtomicBoolean active = new AtomicBoolean(false);
        List<String> logs = new ArrayList<>();
        SdkPromotionHook launch = new SdkPromotionHook(active::get, logs::add, "jos");
        int[] shown = {0}, exits = {0};
        XposedInterface.Chain sdkLauncher = () -> { shown[0]++; return null; };

        // Normal manual launch preserves the original call, return and exception behavior.
        Object intent = new Object();
        check(launch.intercept(() -> intent) == intent, "manual getter changed");
        launch.intercept(sdkLauncher);
        check(shown[0] == 1 && logs.isEmpty(), "manual notice suppressed");
        RuntimeException original = new RuntimeException("original SDK failure");
        try { launch.intercept(() -> { throw original; }); throw new AssertionError("failure lost"); }
        catch (RuntimeException actual) { check(actual == original, "failure replaced"); }

        // Suppressing the launcher does not abort the SDK's outer success/analytics callback.
        active.set(true);
        launch.intercept(sdkLauncher);
        exits[0]++;
        check(shown[0] == 1 && exits[0] == 1, "launcher or enclosing callback changed");
        check(launch.intercept(() -> intent) == null, "legacy Intent not suppressed");
        check(logs.size() == 2 && logs.get(0).equals("sdk_promotion_suppressed:jos"), "missing audit");

        // The same installed hook immediately resumes original behavior when the request ends.
        active.set(false); // cancel, expiry or completed startup, supplied by startupRequest()
        launch.intercept(sdkLauncher);
        check(shown[0] == 2 && logs.size() == 2, "late response still suppressed");
        active.set(true); // another scheduled/verify run in the same process
        launch.intercept(sdkLauncher);
        check(shown[0] == 2 && logs.size() == 3, "next run lost suppression");
        System.out.println("SDK promotion: manual behavior, active suppression, callback continuation, late responses and next run passed");
    }
}
JAVA
"${JAVA_HOME:-/Library/Java/JavaVirtualMachines/temurin-17.jdk/Contents/Home}/bin/javac" -d "$TASK_TMP" \
    "$TASK_TMP/io/github/libxposed/api/XposedInterface.java" \
    "$TASK_TMP/com/zfj/dldlextension/SdkPromotionHook.java" \
    "$TASK_TMP/com/zfj/dldlextension/SdkPromotionTest.java"
"${JAVA_HOME:-/Library/Java/JavaVirtualMachines/temurin-17.jdk/Contents/Home}/bin/java" -cp "$TASK_TMP" com.zfj.dldlextension.SdkPromotionTest
