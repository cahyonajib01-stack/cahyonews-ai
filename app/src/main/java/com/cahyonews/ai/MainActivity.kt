package com.cahyonews.ai

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.work.WorkManager
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Query
import java.time.Instant
import java.time.LocalDate
import java.time.ZoneId
import java.time.format.DateTimeFormatter
import java.util.Locale

data class Event(val name:String,val date:String,val timestamp:Long,val impact:String,val forecast:String,val previous:String,val actual:String?)
data class Market(val symbol:String,val price:Double,val change:Double,val timestamp:Long)
data class Signal(val event:String,val signal:String,val confidence:Int,val bias:String,val reason:String,val generatedAt:Long,val invalidation:String?=null,val entryZone:String?=null,val slLogic:String?=null,val tpLogic:String?=null,val newsRisk:String?=null,val aiStatus:String?=null,val fundamental:Map<String,Any?>?=null,val psychology:Map<String,Any?>?=null,val news:Map<String,Any?>?=null)
data class Dashboard(val nextEvent:Event?,val market:Market?,val signal:Signal?,val daily:Signal?,val events:List<Event>)
data class NewsItem(val headline:String,val summary:String?,val source:String?,val url:String?,val published_at:Long,val category:String?,val sentiment:String?,val xau_score:Double)
data class NewsResponse(val total:Int,val limit:Int,val offset:Int,val items:List<NewsItem>)

interface Api{
    @GET("api/dashboard") suspend fun dashboard():Dashboard
    @GET("api/calendar") suspend fun calendar():List<Event>
    @GET("api/signal") suspend fun signal():Signal
    @GET("api/daily-signal") suspend fun dailySignal():Signal
    @GET("api/intelligence") suspend fun intelligence():Signal
    @GET("api/news/history") suspend fun news(@Query("limit") limit:Int=100,@Query("offset") offset:Int=0,@Query("q") q:String="",@Query("xau_only") xauOnly:Boolean=false):NewsResponse
    @POST("api/news/sync") suspend fun syncNews():Map<String,Any>
}
object ApiClient{ val api:Api by lazy{Retrofit.Builder().baseUrl(BuildConfig.API_BASE_URL).addConverterFactory(GsonConverterFactory.create()).build().create(Api::class.java)} }
private val Bg=Color(0xFF080A0F);private val Card=Color(0xFF11151D);private val Muted=Color(0xFF8B93A3);private val Green=Color(0xFF25D695);private val Red=Color(0xFFFF5C6C);private val Amber=Color(0xFFFFB84D)

class MainActivity:ComponentActivity(){override fun onCreate(savedInstanceState:Bundle?){super.onCreate(savedInstanceState);SignalNotifications.channel(this);scheduleSignalWorker(this);setContent{CahyonewsApp()}}}
@Composable fun CahyonewsApp(){MaterialTheme(colorScheme=darkColorScheme(background=Bg,surface=Card,primary=Green)){var tab by rememberSaveable{mutableIntStateOf(0)};Scaffold(containerColor=Bg,bottomBar={NavigationBar(containerColor=Card){listOf("⌂" to "home","◷" to "calendar","↗" to "signals","📰" to "news","⚙" to "settings").forEachIndexed{i,p->NavigationBarItem(selected=tab==i,onClick={tab=i},icon={Text(p.first,fontSize=19.sp)},label={Text(p.second,fontSize=10.sp)})}}}){p->when(tab){0->Home(Modifier.padding(p));1->Calendar(Modifier.padding(p));2->Signals(Modifier.padding(p));3->News(Modifier.padding(p));else->Settings(Modifier.padding(p))}}}}

@Composable fun Home(m:Modifier){var d by remember{mutableStateOf<Dashboard?>(null)};var error by remember{mutableStateOf<String?>(null)};var auto by rememberSaveable{mutableStateOf(true)};val scope=rememberCoroutineScope();suspend fun load(){try{d=ApiClient.api.dashboard();error=null}catch(e:Exception){error=e.message}};LaunchedEffect(auto){load();while(auto){delay(30000);load()}}
LazyColumn(m.fillMaxSize().padding(16.dp),verticalArrangement=Arrangement.spacedBy(12.dp)){item{Spacer(Modifier.height(8.dp));Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.SpaceBetween){Column{Text("cahyonews ai",fontSize=26.sp,fontWeight=FontWeight.Bold);Text("live economic intelligence",color=Muted,fontSize=12.sp);Text(todayText(),color=Amber,fontSize=12.sp)};Text(if(error==null)"● live" else "● offline",color=if(error==null)Green else Red,fontSize=12.sp)}};item{if(d?.nextEvent!=null)Hero(d!!.nextEvent!!,d!!.signal)else Loading(error)};item{Text("daily xauusd intelligence",fontSize=18.sp,fontWeight=FontWeight.Bold)};item{DailyCard(d?.daily)};item{IntelligenceCard(d?.daily)};item{Text("market",fontSize=18.sp,fontWeight=FontWeight.Bold)};item{MarketCard(d?.market)};item{Text("upcoming events",fontSize=18.sp,fontWeight=FontWeight.Bold)};items(d?.events?:emptyList()){EventCard(it)};item{TextButton(onClick={scope.launch{load()}}){Text("refresh")}}}}

@Composable fun Hero(e:Event,s:Signal?){var now by remember{mutableLongStateOf(System.currentTimeMillis()/1000)};LaunchedEffect(e.timestamp){while(true){delay(1000);now=System.currentTimeMillis()/1000}};val r=maxOf(0,e.timestamp-now);Card(colors=CardDefaults.cardColors(containerColor=Card),shape=RoundedCornerShape(20.dp)){Column(Modifier.padding(18.dp)){Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.SpaceBetween){Text("next high impact",color=Muted);Text(e.impact,color=Red,fontWeight=FontWeight.Bold)};Text(e.name,fontSize=27.sp,fontWeight=FontWeight.Bold);Text(e.date,color=Amber,fontSize=12.sp);Text("%02d : %02d : %02d".format(r/3600,(r%3600)/60,r%60),fontSize=30.sp,fontWeight=FontWeight.Bold);Text("confidence ${s?.confidence?:0}% • ${s?.reason?:"waiting"}",color=Muted,fontSize=11.sp)}}}
@Composable fun DailyCard(s:Signal?){Card(colors=CardDefaults.cardColors(containerColor=Card),shape=RoundedCornerShape(18.dp)){Row(Modifier.fillMaxWidth().padding(18.dp),horizontalArrangement=Arrangement.SpaceBetween,verticalAlignment=Alignment.CenterVertically){Column(Modifier.weight(1f)){Text("XAUUSD",fontSize=22.sp,fontWeight=FontWeight.Bold);Text(s?.bias?:"waiting for live data",color=Muted,fontSize=12.sp);Text(s?.reason?:"",color=Muted,fontSize=11.sp)};Column(horizontalAlignment=Alignment.End){Text(s?.signal?:"WAIT",color=if(s?.signal=="BUY")Green else if(s?.signal=="SELL")Red else Amber,fontSize=24.sp,fontWeight=FontWeight.Bold);Text("${s?.confidence?:0}%",color=Muted)}}}}
@Composable fun IntelligenceCard(s:Signal?){Card(colors=CardDefaults.cardColors(containerColor=Card),shape=RoundedCornerShape(18.dp)){Column(Modifier.padding(18.dp),verticalArrangement=Arrangement.spacedBy(9.dp)){Text("ai intelligence",fontSize=18.sp,fontWeight=FontWeight.Bold);Text("technical • fundamental • psychology • news",color=Muted,fontSize=11.sp);Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.spacedBy(8.dp)){MiniScore("fundamental",s?.fundamental?.get("score")?.toString() ?: "0");MiniScore("psychology",s?.psychology?.get("score")?.toString() ?: "0");MiniScore("news",s?.newsRisk?:"LOW")};Text("ai engine: ${s?.aiStatus?:"—"}",color=Muted,fontSize=10.sp);if(!s?.entryZone.isNullOrBlank())Text("entry zone: ${s?.entryZone}",color=Muted,fontSize=11.sp);if(!s?.invalidation.isNullOrBlank())Text("invalidation: ${s?.invalidation}",color=Muted,fontSize=11.sp);if(!s?.slLogic.isNullOrBlank())Text("sl: ${s?.slLogic}",color=Muted,fontSize=11.sp);if(!s?.tpLogic.isNullOrBlank())Text("tp: ${s?.tpLogic}",color=Muted,fontSize=11.sp)}}}
@Composable fun MiniScore(label:String,value:String){Box(Modifier.weight(1f).background(Color(0xFF171C25),RoundedCornerShape(12.dp)).padding(10.dp)){Column{Text(label,color=Muted,fontSize=9.sp);Text(value,fontWeight=FontWeight.Bold,fontSize=14.sp)}}}
@Composable fun MarketCard(m:Market?){Card(colors=CardDefaults.cardColors(containerColor=Card),shape=RoundedCornerShape(16.dp)){Row(Modifier.fillMaxWidth().padding(16.dp),horizontalArrangement=Arrangement.SpaceBetween){Column{Text("XAUUSD",fontWeight=FontWeight.Bold);Text("live price",color=Muted,fontSize=11.sp)};Column(horizontalAlignment=Alignment.End){Text(if(m==null)"--" else "%.2f".format(m.price),fontSize=22.sp,fontWeight=FontWeight.Bold);Text(if(m==null)"--" else "%+.2f".format(m.change),color=if((m?.change?:0.0)>=0)Green else Red)}}}}
@Composable fun EventCard(e:Event){Card(colors=CardDefaults.cardColors(containerColor=Card),shape=RoundedCornerShape(16.dp)){Column(Modifier.padding(15.dp)){Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.SpaceBetween){Column{Text(e.name,fontWeight=FontWeight.Bold,fontSize=17.sp);Text(e.date,color=Amber,fontSize=11.sp);Text(timeText(e.timestamp),color=Muted,fontSize=12.sp)};Text(e.impact,color=if(e.impact=="HIGH")Red else Amber,fontWeight=FontWeight.Bold,fontSize=11.sp)};Row(horizontalArrangement=Arrangement.spacedBy(12.dp),modifier=Modifier.padding(top=8.dp)){Text("F ${e.forecast.ifBlank{"—"}}",color=Muted,fontSize=10.sp);Text("P ${e.previous.ifBlank{"—"}}",color=Muted,fontSize=10.sp);Text("A ${e.actual?:"—"}",color=Muted,fontSize=10.sp)}}}}
@Composable fun Calendar(m:Modifier){var e by remember{mutableStateOf<List<Event>>(emptyList())};LaunchedEffect(Unit){try{e=ApiClient.api.calendar()}catch(_:Exception){}};LazyColumn(m.fillMaxSize().padding(16.dp),verticalArrangement=Arrangement.spacedBy(12.dp)){item{Text("economic calendar",fontSize=25.sp,fontWeight=FontWeight.Bold);Text("real provider data",color=Muted)};items(e){EventCard(it)}}}
@Composable fun Signals(m:Modifier){var s by remember{mutableStateOf<Signal?>(null)};LaunchedEffect(Unit){try{s=ApiClient.api.intelligence()}catch(_:Exception){}};LazyColumn(m.fillMaxSize().padding(16.dp),verticalArrangement=Arrangement.spacedBy(12.dp)){item{Text("xauusd intelligence",fontSize=25.sp,fontWeight=FontWeight.Bold);Text("technical + fundamental + psychology + news",color=Muted)};item{DailyCard(s)};item{IntelligenceCard(s)}}}

@Composable fun News(m:Modifier){var data by remember{mutableStateOf<NewsResponse?>(null)};var q by rememberSaveable{mutableStateOf("")};var xauOnly by rememberSaveable{mutableStateOf(true)};var loading by remember{mutableStateOf(false)};val scope=rememberCoroutineScope();suspend fun load(){loading=true;try{data=ApiClient.api.news(100,0,q,xauOnly)}catch(_:Exception){};loading=false};LaunchedEffect(xauOnly){load()};Column(m.fillMaxSize().padding(16.dp)){Text("news archive",fontSize=25.sp,fontWeight=FontWeight.Bold);Text("persisten: berita yang berhasil diambil provider",color=Muted,fontSize=11.sp);Spacer(Modifier.height(10.dp));Row(horizontalArrangement=Arrangement.spacedBy(8.dp),verticalAlignment=Alignment.CenterVertically){OutlinedTextField(value=q,onValueChange={q=it},modifier=Modifier.weight(1f),singleLine=true,label={Text("search")});Button(onClick={scope.launch{load()}}){Text("go")}};Row(verticalAlignment=Alignment.CenterVertically){Text("xauusd only",color=Muted);Switch(xauOnly,{xauOnly=it});Spacer(Modifier.weight(1f));Text(if(loading)"syncing…" else "${data?.total?:0} articles",color=Muted,fontSize=11.sp)};LazyColumn(verticalArrangement=Arrangement.spacedBy(9.dp)){items(data?.items?:emptyList()){n->NewsCard(n)}}}}
@Composable fun NewsCard(n:NewsItem){Card(colors=CardDefaults.cardColors(containerColor=Card),shape=RoundedCornerShape(15.dp)){Column(Modifier.padding(14.dp),verticalArrangement=Arrangement.spacedBy(5.dp)){Text(n.headline,fontWeight=FontWeight.SemiBold,fontSize=15.sp);Text("${n.source?:"source"} • ${timeText(n.published_at)} • xau ${"%.1f".format(n.xau_score)}",color=Amber,fontSize=10.sp);if(!n.summary.isNullOrBlank())Text(n.summary!!,color=Muted,fontSize=11.sp)}}}

@Composable fun Settings(m:Modifier){var notifications by rememberSaveable{mutableStateOf(true)};var auto by rememberSaveable{mutableStateOf(true)};var ai by rememberSaveable{mutableStateOf(true)};val context=androidx.compose.ui.platform.LocalContext.current;Column(m.fillMaxSize().padding(16.dp),verticalArrangement=Arrangement.spacedBy(14.dp)){Text("settings",fontSize=25.sp,fontWeight=FontWeight.Bold);Setting("notifications","high impact + daily XAUUSD signal",notifications){notifications=it;if(it)scheduleSignalWorker(context)else WorkManager.getInstance(context).cancelUniqueWork("cahyonews_signal_worker")};Setting("auto refresh","market + calendar",auto){auto=it};Setting("ai analysis","macro + technical + psychology + news",ai){ai=it};Text("cahyonews ai v9.0 • real-provider architecture",color=Muted,fontSize=12.sp);Text("backend url is configured at build time; use HTTPS for a physical phone.",color=Muted,fontSize=11.sp)}}
@Composable fun Setting(t:String,d:String,c:Boolean,on:(Boolean)->Unit){Card(colors=CardDefaults.cardColors(containerColor=Card),shape=RoundedCornerShape(16.dp)){Row(Modifier.fillMaxWidth().padding(16.dp),verticalAlignment=Alignment.CenterVertically){Column(Modifier.weight(1f)){Text(t,fontWeight=FontWeight.SemiBold);Text(d,color=Muted,fontSize=11.sp)};Switch(checked=c,onCheckedChange=on)}}}
@Composable fun Loading(error:String?){Text(error?:"loading live data…",color=Muted)}
fun todayText()=LocalDate.now().format(DateTimeFormatter.ofPattern("EEEE, dd MMMM yyyy",Locale.ENGLISH))
fun timeText(ts:Long)=Instant.ofEpochSecond(ts).atZone(ZoneId.systemDefault()).format(DateTimeFormatter.ofPattern("dd MMM HH:mm"))
