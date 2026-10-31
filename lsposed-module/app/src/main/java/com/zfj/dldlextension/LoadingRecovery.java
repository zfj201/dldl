package com.zfj.dldlextension;

/** Shared monotonic, request-bound budget for the SDK dialog and health-advice splash. */
final class LoadingRecovery {
    static final long STUCK_MS=15_000;
    static final int MAX_RESTARTS=3;
    static final String SDK_SAMPLE="sdk-loading.tsv";
    static final String SPLASH_SAMPLE="startup-splash.tsv";
    static boolean validSampleFile(String name) {return SDK_SAMPLE.equals(name) || SPLASH_SAMPLE.equals(name);}
    enum Decision { NONE, RESTART, EXHAUSTED }
    private boolean advanced;
    private int restarts;

    int restarts() { return restarts; }
    void restarted() { restarts++; }

    boolean observing(String id,String startup) {
        String[] s=startup.trim().split("\t");
        if (s.length>=4 && s[1].equals(id)
                && !(s[2].equals("waiting") && s[3].equals("waiting_sdk_or_login"))) advanced=true;
        return !advanced;
    }

    Decision inspect(String sample,String id,String startup,long now) {
        if (!observing(id,startup)) return Decision.NONE;
        String[] p=sample.trim().split("\t");
        if (p.length!=6 || !p[0].equals("v1") || !p[1].equals(id)) return Decision.NONE;
        try {
            long pid=Long.parseLong(p[2]),since=Long.parseLong(p[3]),observed=Long.parseLong(p[4]);
            // A stuck UI thread may stop sampling too; the service still measures elapsed time.
            // RootAccess re-checks the current window and sample before stopping the process.
            if (!p[5].equals("visible") || pid<=0 || since<0 || observed<since || observed>now
                    || now-since<=STUCK_MS) return Decision.NONE;
            if (restarts>=MAX_RESTARTS) return Decision.EXHAUSTED;
            return Decision.RESTART;
        } catch (NumberFormatException e) { return Decision.NONE; }
    }
}
