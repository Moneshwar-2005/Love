package ai.love.assistant;

import android.content.Context;
import android.content.SharedPreferences;
import android.security.keystore.KeyGenParameterSpec;
import android.security.keystore.KeyInfo;
import android.security.keystore.KeyProperties;
import android.util.Base64;
import com.getcapacitor.JSObject;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;
import java.nio.charset.StandardCharsets;
import java.security.KeyFactory;
import java.security.KeyStore;
import java.security.SecureRandom;
import javax.crypto.Cipher;
import javax.crypto.KeyGenerator;
import javax.crypto.SecretKey;
import javax.crypto.SecretKeyFactory;
import javax.crypto.spec.GCMParameterSpec;

/**
 * LOVE Native Android Keystore Plugin.
 * Provides hardware-backed (TEE / StrongBox) AES-256-GCM authenticated encryption
 * for sensitive session credentials, tokens, and encryption keys.
 */
@CapacitorPlugin(name = "LoveKeystore")
public class LoveKeystorePlugin extends Plugin {

    private static final String ANDROID_KEYSTORE = "AndroidKeyStore";
    private static final String MASTER_KEY_ALIAS = "love_master_key_alias";
    private static final String PREF_NAME = "love_keystore_vault";
    private static final String CIPHER_TRANSFORMATION = "AES/GCM/NoPadding";
    private static final int GCM_IV_LENGTH_BYTES = 12;
    private static final int GCM_TAG_LENGTH_BITS = 128;

    private SharedPreferences sharedPreferences;

    @Override
    public void load() {
        super.load();
        Context context = getContext();
        sharedPreferences = context.getSharedPreferences(PREF_NAME, Context.MODE_PRIVATE);
        ensureMasterKeyExists();
    }

    private synchronized void ensureMasterKeyExists() {
        try {
            KeyStore keyStore = KeyStore.getInstance(ANDROID_KEYSTORE);
            keyStore.load(null);
            if (!keyStore.containsAlias(MASTER_KEY_ALIAS)) {
                KeyGenerator keyGenerator = KeyGenerator.getInstance(
                    KeyProperties.KEY_ALGORITHM_AES,
                    ANDROID_KEYSTORE
                );
                KeyGenParameterSpec.Builder builder = new KeyGenParameterSpec.Builder(
                    MASTER_KEY_ALIAS,
                    KeyProperties.PURPOSE_ENCRYPT | KeyProperties.PURPOSE_DECRYPT
                )
                    .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
                    .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                    .setKeySize(256)
                    .setRandomizedEncryptionRequired(true);

                keyGenerator.init(builder.build());
                keyGenerator.generateKey();
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    private SecretKey getMasterKey() throws Exception {
        KeyStore keyStore = KeyStore.getInstance(ANDROID_KEYSTORE);
        keyStore.load(null);
        KeyStore.SecretKeyEntry entry = (KeyStore.SecretKeyEntry) keyStore.getEntry(MASTER_KEY_ALIAS, null);
        if (entry == null) {
            ensureMasterKeyExists();
            keyStore.load(null);
            entry = (KeyStore.SecretKeyEntry) keyStore.getEntry(MASTER_KEY_ALIAS, null);
        }
        return entry.getSecretKey();
    }

    @PluginMethod
    public void setSecureItem(PluginCall call) {
        String key = call.getString("key");
        String value = call.getString("value");

        if (key == null || value == null) {
            call.reject("Key and value must not be null");
            return;
        }

        try {
            SecretKey secretKey = getMasterKey();
            Cipher cipher = Cipher.getInstance(CIPHER_TRANSFORMATION);

            // With setRandomizedEncryptionRequired(true), AndroidKeyStore generates the cryptographically random IV
            cipher.init(Cipher.ENCRYPT_MODE, secretKey);
            byte[] iv = cipher.getIV();
            byte[] cipherBytes = cipher.doFinal(value.getBytes(StandardCharsets.UTF_8));

            // Format: Base64(IV):Base64(CipherBytes)
            String ivB64 = Base64.encodeToString(iv, Base64.NO_WRAP);
            String cipherB64 = Base64.encodeToString(cipherBytes, Base64.NO_WRAP);
            String combined = ivB64 + ":" + cipherB64;

            sharedPreferences.edit().putString(key, combined).apply();

            JSObject ret = new JSObject();
            ret.put("success", true);
            call.resolve(ret);
        } catch (Exception e) {
            call.reject("Android Keystore encryption failed: " + e.getMessage(), e);
        }
    }

    @PluginMethod
    public void getSecureItem(PluginCall call) {
        String key = call.getString("key");
        if (key == null) {
            call.reject("Key must not be null");
            return;
        }

        try {
            String combined = sharedPreferences.getString(key, null);
            JSObject ret = new JSObject();

            if (combined == null) {
                ret.put("value", null);
                call.resolve(ret);
                return;
            }

            String[] parts = combined.split(":");
            if (parts.length != 2) {
                // Malformed or legacy entry, clear and return null
                sharedPreferences.edit().remove(key).apply();
                ret.put("value", null);
                call.resolve(ret);
                return;
            }

            byte[] iv = Base64.decode(parts[0], Base64.NO_WRAP);
            byte[] cipherBytes = Base64.decode(parts[1], Base64.NO_WRAP);

            SecretKey secretKey = getMasterKey();
            Cipher cipher = Cipher.getInstance(CIPHER_TRANSFORMATION);
            GCMParameterSpec spec = new GCMParameterSpec(GCM_TAG_LENGTH_BITS, iv);
            cipher.init(Cipher.DECRYPT_MODE, secretKey, spec);

            byte[] plainBytes = cipher.doFinal(cipherBytes);
            String plainText = new String(plainBytes, StandardCharsets.UTF_8);

            ret.put("value", plainText);
            call.resolve(ret);
        } catch (Exception e) {
            call.reject("Android Keystore decryption failed: " + e.getMessage(), e);
        }
    }

    @PluginMethod
    public void removeSecureItem(PluginCall call) {
        String key = call.getString("key");
        if (key != null) {
            sharedPreferences.edit().remove(key).apply();
        }
        JSObject ret = new JSObject();
        ret.put("success", true);
        call.resolve(ret);
    }

    @PluginMethod
    public void clearSecureStore(PluginCall call) {
        sharedPreferences.edit().clear().apply();
        JSObject ret = new JSObject();
        ret.put("success", true);
        call.resolve(ret);
    }

    @PluginMethod
    public void isHardwareBacked(PluginCall call) {
        boolean isHw = false;
        try {
            SecretKey secretKey = getMasterKey();
            SecretKeyFactory factory = SecretKeyFactory.getInstance(
                secretKey.getAlgorithm(),
                ANDROID_KEYSTORE
            );
            KeyInfo keyInfo = (KeyInfo) factory.getKeySpec(secretKey, KeyInfo.class);
            isHw = keyInfo.isInsideSecureHardware();
        } catch (Exception e) {
            // Emulators or devices without hardware TEE
            isHw = false;
        }

        JSObject ret = new JSObject();
        ret.put("isHardwareBacked", isHw);
        ret.put("provider", ANDROID_KEYSTORE);
        call.resolve(ret);
    }
}
