#!/bin/sh
set -eu
ROOT=$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)
TASK_TMP=$(mktemp -d)
trap 'rm -rf "$TASK_TMP"' EXIT
mkdir -p "$TASK_TMP/com/zfj/dldlextension"
cp "$ROOT/lsposed-module/app/src/main/java/com/zfj/dldlextension/ExecutionProgress.java" "$TASK_TMP/com/zfj/dldlextension/"
cat > "$TASK_TMP/com/zfj/dldlextension/ExecutionProgressTest.java" <<'JAVA'
package com.zfj.dldlextension;
public class ExecutionProgressTest {
 static String row(String id,String status,long polled,long confirmed) {
  return "v1\t"+id+"\t"+status+"\texecuting\t2\t10\t"+polled+"\t"+confirmed+"\n";
 }
 public static void main(String[] args) {
  ExecutionProgress p=new ExecutionProgress();
  if(!p.advanced(row("run","running",1000,1000),"run",1000)) throw new AssertionError("first progress");
  for(String s:new String[]{row("other","running",1010,1010),row("run","completed",1010,1010),
    row("run","running",1010,1000),row("run","running",900,1100),row("run","running",9999,9999),
    "v1\trun\trunning\texecuting\t1\t10\t1010\tbad", "v1\trun\trunning\texecuting\t1\t10\t1010"})
   if(p.advanced(s,"run",1010)) throw new AssertionError(s);
  if(p.advanced(row("run","running",1001,1001),"run",1200)) throw new AssertionError("stale file");
  if(p.advanced(row("run","running",1300,1001),"run",1300)) throw new AssertionError("polling is not progress");
  for(int i=1;i<1000;i++) if(!p.advanced(row("run","running",1000+i*20,1000+i*20),"run",1000+i*20)) throw new AssertionError("long run");
  System.out.println("ExecutionProgress: active long runs, stall, stale/malformed/wrong-run reports passed");
 }
}
JAVA
javac -d "$TASK_TMP" "$TASK_TMP/com/zfj/dldlextension/ExecutionProgress.java" "$TASK_TMP/com/zfj/dldlextension/ExecutionProgressTest.java"
java -cp "$TASK_TMP" com.zfj.dldlextension.ExecutionProgressTest
