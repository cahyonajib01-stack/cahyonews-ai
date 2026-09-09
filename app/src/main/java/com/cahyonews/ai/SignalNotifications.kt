package com.cahyonews.ai

import android.app.*
import android.content.*
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.work.*
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.util.concurrent.TimeUnit

object SignalNotifications {
    const val CHANNEL="cahyonews_ai_signals"
    const val EVENT_ID=5101
    const val DAILY_ID=5102

    fun channel(context: Context){
        if(Build.VERSION.SDK_INT>=26){
            val nm=context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
            nm.createNotificationChannel(NotificationChannel(CHANNEL,"Cahyonews AI Signals",NotificationManager.IMPORTANCE_HIGH))
        }
    }

    fun show(context:Context,title:String,body:String,id:Int){
        channel(context)
        val n=NotificationCompat.Builder(context,CHANNEL)
            .setSmallIcon(android.R.drawable.ic_dialog_info)
            .setContentTitle(title)
            .setContentText(body)
            .setStyle(NotificationCompat.BigTextStyle().bigText(body))
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .setAutoCancel(true).build()
        (context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager).notify(id,n)
    }
}

class SignalWorker(app:Context,params:WorkerParameters):CoroutineWorker(app,params){
    override suspend fun doWork():Result = try{
        val api=ApiClient.api
        val d=api.dashboard()
        val event=d.nextEvent
        val sig=d.signal
        if(event!=null && sig!=null){
            SignalNotifications.show(
                applicationContext,
                "Cahyonews AI • ${event.name}",
                "${sig.signal} XAUUSD • confidence ${sig.confidence}%\n${sig.bias} • ${sig.reason}"
                ,SignalNotifications.EVENT_ID)
        }
        val daily=api.dailySignal()
        SignalNotifications.show(
            applicationContext,
            "Cahyonews AI • Daily XAUUSD",
            "${daily.signal} XAUUSD • confidence ${daily.confidence}%\n${daily.bias}\n${daily.reason}",
            SignalNotifications.DAILY_ID
        )
        Result.success()
    }catch(_:Throwable){ Result.retry() }
}

fun scheduleSignalWorker(context:Context){
    SignalNotifications.channel(context)
    val req=PeriodicWorkRequestBuilder<SignalWorker>(15,TimeUnit.MINUTES)
        .setConstraints(Constraints.Builder().setRequiredNetworkType(NetworkType.CONNECTED).build())
        .build()
    WorkManager.getInstance(context).enqueueUniquePeriodicWork(
        "cahyonews_signal_worker",ExistingPeriodicWorkPolicy.UPDATE,req)
}

class BootReceiver:BroadcastReceiver(){
    override fun onReceive(context:Context,intent:Intent?){
        if(intent?.action==Intent.ACTION_BOOT_COMPLETED) scheduleSignalWorker(context)
    }
}
