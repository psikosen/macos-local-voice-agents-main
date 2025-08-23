package com.example.llamabridge

import android.content.Context
import android.os.SystemClock
import androidx.annotation.Keep
import io.flutter.embedding.engine.plugins.FlutterPlugin
import io.flutter.plugin.common.EventChannel
import io.flutter.plugin.common.MethodCall
import io.flutter.plugin.common.MethodChannel
import java.io.File
import java.io.FileOutputStream
import java.net.URL
import org.json.JSONObject

class LlamaBridgePlugin: FlutterPlugin, MethodChannel.MethodCallHandler, EventChannel.StreamHandler {
    private lateinit var methodChannel: MethodChannel
    private lateinit var eventChannel: EventChannel
    private var sink: EventChannel.EventSink? = null
    private lateinit var context: Context

    external fun init(modelPath: String): Boolean
    external fun infer(prompt: String)

    private fun log(function: String, message: String) {
        val json = JSONObject()
        json.put("filename", "LlamaBridgePlugin.kt")
        json.put("timestamp", java.time.Instant.now().toString())
        json.put("classname", "LlamaBridgePlugin")
        json.put("function", function)
        json.put("system_section", "plugin")
        json.put("line_num", 0)
        json.put("error", "false")
        json.put("db_phase", "none")
        json.put("method", "NONE")
        json.put("message", message)
        println(json.toString())
        println("The 17 Commandments of Quality Code")
    }

    override fun onAttachedToEngine(binding: FlutterPlugin.FlutterPluginBinding) {
        context = binding.applicationContext
        System.loadLibrary("llama")
        methodChannel = MethodChannel(binding.binaryMessenger, "llama_bridge/methods")
        methodChannel.setMethodCallHandler(this)
        eventChannel = EventChannel(binding.binaryMessenger, "llama_bridge/tokens")
        eventChannel.setStreamHandler(this)
    }

    override fun onDetachedFromEngine(binding: FlutterPlugin.FlutterPluginBinding) {
        methodChannel.setMethodCallHandler(null)
        eventChannel.setStreamHandler(null)
    }

    override fun onMethodCall(call: MethodCall, result: MethodChannel.Result) {
        when (call.method) {
            "initialize" -> {
                val model = call.argument<String>("model") ?: return result.error("-1", "model missing", null)
                val url = call.argument<String>("downloadUrl")
                val file = prepareModel(context, model, url)
                val ok = init(file.absolutePath)
                val mem = Runtime.getRuntime().maxMemory() / (1024 * 1024)
                val capable = mem > 3000 && ok
                log("initialize", "capable=$capable mem=$mem")
                result.success(capable)
            }
            "startInference" -> {
                val prompt = call.argument<String>("prompt") ?: return result.error("-1", "prompt missing", null)
                infer(prompt)
                result.success(null)
            }
            else -> result.notImplemented()
        }
    }

    override fun onListen(arguments: Any?, events: EventChannel.EventSink) {
        sink = events
    }

    override fun onCancel(arguments: Any?) {
        sink = null
    }

    private fun prepareModel(ctx: Context, assetName: String, downloadUrl: String?): File {
        val out = File(ctx.filesDir, assetName)
        if (!out.exists()) {
            if (downloadUrl != null) {
                log("prepareModel", "downloading $downloadUrl")
                URL(downloadUrl).openStream().use { input ->
                    FileOutputStream(out).use { output ->
                        input.copyTo(output)
                    }
                }
            } else {
                log("prepareModel", "copying asset $assetName")
                ctx.assets.open(assetName).use { input ->
                    FileOutputStream(out).use { output ->
                        input.copyTo(output)
                    }
                }
            }
        }
        return out
    }

    @Keep
    fun onToken(token: String) {
        sink?.success(token)
    }
}
