#!/bin/sh
set -eu
ROOT=$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)
TASK_TMP=$(mktemp -d)
trap 'rm -rf "$TASK_TMP"' EXIT
mkdir -p "$TASK_TMP/com/zfj/dldlextension"
cp "$ROOT/lsposed-module/app/src/main/java/com/zfj/dldlextension/LaunchRequest.java" "$TASK_TMP/com/zfj/dldlextension/"
cat > "$TASK_TMP/com/zfj/dldlextension/LaunchRequestTest.java" <<'JAVA'
package com.zfj.dldlextension;
public class LaunchRequestTest {
    public static void main(String[] args) {
        String valid="v1\trun-1\t11\tsrv\t1000\t1300\tverify\n";
        if (LaunchRequest.parse(valid,1000)==null) throw new AssertionError("valid");
        for (String bad:new String[]{valid.replace("run-1","../run"),valid.replace("1300","1301"),
                valid.replace("1000","-1"),valid.replace("1300","999"),valid.replace("verify","purchase"),
                valid.replace("1000","99999999999999999999999999999"),valid+"\n"}) {
            if(LaunchRequest.parse(bad,1000)!=null) throw new AssertionError(bad);
        }
        if(LaunchRequest.parse(valid,1301)!=null || LaunchRequest.parse(valid,994)!=null) throw new AssertionError("time");
        System.out.println("Java launch protocol: validation and expiry passed");
    }
}
JAVA
"${JAVA_HOME:-/Library/Java/JavaVirtualMachines/temurin-17.jdk/Contents/Home}/bin/javac" -d "$TASK_TMP" "$TASK_TMP/com/zfj/dldlextension/LaunchRequest.java" "$TASK_TMP/com/zfj/dldlextension/LaunchRequestTest.java"
"${JAVA_HOME:-/Library/Java/JavaVirtualMachines/temurin-17.jdk/Contents/Home}/bin/java" -cp "$TASK_TMP" com.zfj.dldlextension.LaunchRequestTest
