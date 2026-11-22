package ai.love.assistant;

import android.os.Handler;
import android.os.Looper;
import androidx.annotation.NonNull;
import androidx.biometric.BiometricManager;
import androidx.biometric.BiometricPrompt;
import androidx.core.content.ContextCompat;
import androidx.fragment.app.FragmentActivity;
import com.getcapacitor.JSObject;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;
import java.util.concurrent.Executor;

/**
 * LOVE Native Android Biometrics Plugin.
 * Interfaces directly with Android Jetpack BiometricPrompt and BiometricManager
 * to provide hardware-verified biometric authentication (Fingerprint, Face Unlock)
 * and secure credential gating.
 */
@CapacitorPlugin(name = "LoveBiometric")
public class LoveBiometricPlugin extends Plugin {

    @PluginMethod
    public void checkBiometricAvailability(PluginCall call) {
        BiometricManager biometricManager = BiometricManager.from(getContext());
        int authenticators = BiometricManager.Authenticators.BIOMETRIC_STRONG | BiometricManager.Authenticators.BIOMETRIC_WEAK;
        int canAuth = biometricManager.canAuthenticate(authenticators);

        JSObject ret = new JSObject();
        switch (canAuth) {
            case BiometricManager.BIOMETRIC_SUCCESS:
                ret.put("isAvailable", true);
                ret.put("hasEnrolledBiometrics", true);
                ret.put("status", "BIOMETRIC_SUCCESS");
                ret.put("biometryType", "fingerprint");
                break;
            case BiometricManager.BIOMETRIC_ERROR_NONE_ENROLLED:
                ret.put("isAvailable", true);
                ret.put("hasEnrolledBiometrics", false);
                ret.put("status", "BIOMETRIC_ERROR_NONE_ENROLLED");
                ret.put("biometryType", "none");
                break;
            case BiometricManager.BIOMETRIC_ERROR_NO_HARDWARE:
                ret.put("isAvailable", false);
                ret.put("hasEnrolledBiometrics", false);
                ret.put("status", "BIOMETRIC_ERROR_NO_HARDWARE");
                ret.put("biometryType", "none");
                break;
            case BiometricManager.BIOMETRIC_ERROR_HW_UNAVAILABLE:
                ret.put("isAvailable", false);
                ret.put("hasEnrolledBiometrics", false);
                ret.put("status", "BIOMETRIC_ERROR_HW_UNAVAILABLE");
                ret.put("biometryType", "none");
                break;
            default:
                ret.put("isAvailable", false);
                ret.put("hasEnrolledBiometrics", false);
                ret.put("status", "BIOMETRIC_STATUS_UNKNOWN");
                ret.put("biometryType", "none");
                break;
        }

        call.resolve(ret);
    }

    @PluginMethod
    public void authenticate(PluginCall call) {
        String title = call.getString("title", "Unlock LOVE Assistant");
        String subtitle = call.getString("subtitle", "Confirm your identity to access personal memory and tools");
        String negativeText = call.getString("cancelText", "Use Password");

        if (!(getActivity() instanceof FragmentActivity)) {
            call.reject("Activity is not a FragmentActivity required by BiometricPrompt");
            return;
        }

        final FragmentActivity activity = (FragmentActivity) getActivity();
        final Handler mainHandler = new Handler(Looper.getMainLooper());

        mainHandler.post(() -> {
            try {
                Executor executor = ContextCompat.getMainExecutor(activity);
                BiometricPrompt biometricPrompt = new BiometricPrompt(
                    activity,
                    executor,
                    new BiometricPrompt.AuthenticationCallback() {
                        @Override
                        public void onAuthenticationError(int errorCode, @NonNull CharSequence errString) {
                            super.onAuthenticationError(errorCode, errString);
                            JSObject ret = new JSObject();
                            ret.put("authenticated", false);
                            ret.put("errorCode", errorCode);
                            ret.put("message", errString.toString());
                            call.resolve(ret);
                        }

                        @Override
                        public void onAuthenticationSucceeded(@NonNull BiometricPrompt.AuthenticationResult result) {
                            super.onAuthenticationSucceeded(result);
                            JSObject ret = new JSObject();
                            ret.put("authenticated", true);
                            call.resolve(ret);
                        }

                        @Override
                        public void onAuthenticationFailed() {
                            super.onAuthenticationFailed();
                            // Keep prompt active for retry
                        }
                    }
                );

                BiometricPrompt.PromptInfo promptInfo = new BiometricPrompt.PromptInfo.Builder()
                    .setTitle(title)
                    .setSubtitle(subtitle)
                    .setNegativeButtonText(negativeText)
                    .setAllowedAuthenticators(BiometricManager.Authenticators.BIOMETRIC_STRONG | BiometricManager.Authenticators.BIOMETRIC_WEAK)
                    .build();

                biometricPrompt.authenticate(promptInfo);
            } catch (Exception e) {
                call.reject("Failed to display native BiometricPrompt: " + e.getMessage(), e);
            }
        });
    }
}
