package com.zfj.dldlextension;

/** Accept confirmed queue progress, not the continually updated polling timestamp. */
final class ExecutionProgress {
    private long last;
    boolean advanced(String text,String runId,long nowSeconds) {
        if (text==null || text.length()>1024) return false;
        String[] p=text.trim().split("\t");
        if (p.length!=8 || !p[0].equals("v1") || !p[1].equals(runId) || !p[2].equals("running")) return false;
        try {
            long observed=Long.parseLong(p[6]),progress=Long.parseLong(p[7]);
            if (progress<=last || progress<=0 || observed<progress || observed>nowSeconds+5
                    || nowSeconds-observed>30 || nowSeconds-progress>180) return false;
            last=progress;return true;
        } catch (NumberFormatException invalid) {return false;}
    }
}
