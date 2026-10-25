package com.zfj.dldlextension;

import java.util.function.BooleanSupplier;
import java.util.function.Consumer;
import io.github.libxposed.api.XposedInterface;

/** Only attach to optional promotion getters / launchers, never general Activity APIs. */
final class SdkPromotionHook implements XposedInterface.Hooker {
    private final BooleanSupplier startupActive;
    private final Consumer<String> record;
    private final String source;

    SdkPromotionHook(BooleanSupplier startupActive, Consumer<String> record, String source) {
        this.startupActive = startupActive;
        this.record = record;
        this.source = source;
    }

    @Override public Object intercept(XposedInterface.Chain chain) throws Throwable {
        // Recheck for every callback: a late response after cancel/expiry must run normally.
        if (!startupActive.getAsBoolean()) return chain.proceed();
        record.accept("sdk_promotion_suppressed:" + source);
        // All targets return Intent or void. The SDK's surrounding callback still runs.
        return null;
    }
}
