import os
import re
import math
import requests
import logging
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler, ContextTypes
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp

# --- 1. الإعدادات والبيانات ---
TOKEN = "8422973831:AAExcIH_XH9PDImbyv_Ejr4eYH0pDYzRGzk"
OSRM_SOURCE = os.getenv('OSRM_URL', 'http://127.0.0.1:5000')

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

LOCATION, TRIP_MODE, ASK_ATTENDANCE, GET_MISSING = range(4)

# ثوابت الواقعية
TRAFFIC_MULTIPLIER = 1.4      
SERVICE_TIME_PER_STOP = 180   
SOFT_CAPACITY_LIMIT = 6       
HARD_CAPACITY_LIMIT = 8       
CROWDING_PENALTY = 5000       # رفعنا العقوبة قليلاً لتفضيل توزيع الركاب

# --- بيانات السائقين ---
MASTER_DRIVERS = [
    {"id": 1, "name": "أبو حسن", "lat": 24.807778, "lng": 46.635056},
    {"id": 2, "name": "أبو مالك", "lat": 24.808083, "lng": 46.647889},
    {"id": 3, "name": "أبو إبراهيم", "lat": 24.810361, "lng": 46.666028},
    {"id": 4, "name": "أبو يوسف", "lat": 24.821333, "lng": 46.633889},
    {"id": 5, "name": "أبو عمر", "lat": 24.821333, "lng": 46.633889},     
    {"id": 6, "name": "أبو عبدالله", "lat": 24.821333, "lng": 46.633889}, 
    {"id": 7, "name": "أبو حمد", "lat": 24.822889, "lng": 46.635444}
]

# --- بيانات الركاب ---
MASTER_PASSENGERS = [
    {"id": 8, "name": "بيت الحيد", "lat": 24.80225, "lng": 46.64806},
    {"id": 9, "name": "بيت الفايز", "lat": 24.821333, "lng": 46.633889}, 
    {"id": 10, "name": "بيت ابراهيم السياري", "lat": 24.83697, "lng": 46.66928},
    {"id": 11, "name": "بيت عزام المطيري", "lat": 24.81623, "lng": 46.63978},
    {"id": 12, "name": "بيت زياد المنصور", "lat": 24.83022, "lng": 46.55867},
    {"id": 13, "name": "بيت يزيد المعارك", "lat": 24.821333, "lng": 46.633889}, 
    {"id": 14, "name": "بيت ابو جبارة", "lat": 24.81339, "lng": 46.63464},
    {"id": 15, "name": "بيت عمر البراك", "lat": 24.79266, "lng": 46.62463},
    {"id": 16, "name": "بيت الحميضي", "lat": 24.67708, "lng": 46.66886},
    {"id": 17, "name": "بيت الصقعبي الاصلي", "lat": 24.83486, "lng": 46.65306},
    {"id": 18, "name": "بيت عبدالله الرميح", "lat": 24.77858, "lng": 46.63378},
    {"id": 19, "name": "بيت محمد البراهيم", "lat": 24.80650, "lng": 46.64272},
    {"id": 20, "name": "بيت فهد الرومي", "lat": 24.79958, "lng": 46.63844},
    {"id": 21, "name": "بيت خوال الصقعبي", "lat": 24.79492, "lng": 46.62199},
    {"id": 22, "name": "بيت مالك السياري", "lat": 24.83697, "lng": 46.66939},
    {"id": 23, "name": "بيت السلطان", "lat": 24.87125, "lng": 46.65403},
    {"id": 24, "name": "بيت الشتوي", "lat": 24.83533, "lng": 46.67764},
    {"id": 25, "name": "بيت المرشد", "lat": 24.82800, "lng": 46.57786},
    {"id": 26, "name": "بيت علي العش", "lat": 24.80840, "lng": 46.64753},
    {"id": 27, "name": "بيت الشيبان", "lat": 24.80100, "lng": 46.63544},
    {"id": 28, "name": "بيت محمد الاحمد", "lat": 24.82100, "lng": 46.64025},
    {"id": 29, "name": "بيت الفيفي", "lat": 24.82247, "lng": 46.64006},
    {"id": 30, "name": "بيت فارس الدواي", "lat": 24.82864, "lng": 46.65299},
    {"id": 31, "name": "بيت عمر السلمان", "lat": 24.83853, "lng": 46.65072},
    # تم فصل حازم ومحمد الدهيشي ليتم حسابهم كراكبين (مقعدين)
    {"id": 32, "name": "بيت حازم الدهيشي", "lat": 24.82694, "lng": 46.65461},
    {"id": 33, "name": "بيت محمد الدهيشي", "lat": 24.82694, "lng": 46.65461}
]

# --- 2. الوظائف المساعدة (نفس السابق) ---

def parse_coords(user_input):
    user_input = user_input.strip()
    coord_match = re.match(r'^(\d+\.\d+),\s*(\d+\.\d+)$', user_input.replace(" ", ""))
    if coord_match: return {"name": "نقطة التجمع", "lat": float(coord_match.group(1)), "lng": float(coord_match.group(2))}
    try:
        resp = requests.get(user_input, allow_redirects=True, timeout=5)
        match = re.search(r'(@|search/|q=)(-?\d+\.\d+),(-?\d+\.\d+)', resp.url)
        if match: return {"name": "نقطة التجمع", "lat": float(match.group(2)), "lng": float(match.group(3))}
    except: pass
    return None

def get_osrm_matrix(locations):
    coords_string = ";".join([f"{loc['lng']},{loc['lat']}" for loc in locations])
    url = f"{OSRM_SOURCE}/table/v1/driving/{coords_string}?annotations=duration"
    try:
        resp = requests.get(url)
        data = resp.json()
        if 'durations' not in data: return None
        return [[999999 if x is None else int(x + 0.5) for x in row] for row in data['durations']]
    except: return None

def create_google_link(route_indices, all_locations):
    if len(route_indices) < 2: return "لا يوجد مسار"
    base_url = "https://www.google.com/maps/dir/?api=1"
    start_loc = all_locations[route_indices[0]]
    origin = f"&origin={start_loc['lat']},{start_loc['lng']}"
    end_loc = all_locations[route_indices[-1]]
    destination = f"&destination={end_loc['lat']},{end_loc['lng']}"
    
    waypoints_str = ""
    if len(route_indices) > 2:
        middle_indices = route_indices[1:-1]
        wp_list = [f"{all_locations[i]['lat']},{all_locations[i]['lng']}" for i in middle_indices]
        waypoints_str = "&waypoints=" + "|".join(wp_list) + "&travelmode=driving"
    return base_url + origin + destination + waypoints_str

# --- 3. المحرك الرئيسي (SOLVER) ---

def solve_vrp(active_drivers, active_passengers, meeting_point, mode):
    all_locations = active_drivers + active_passengers + [meeting_point]
    num_drivers = len(active_drivers)
    meeting_idx = len(all_locations) - 1
    
    if num_drivers == 0: return "خطأ: لا يوجد سائقين متاحين."
    if len(active_passengers) == 0: return "خطأ: لا يوجد ركاب."
    
    time_matrix = get_osrm_matrix(all_locations)
    if not time_matrix: return "خطأ: سيرفر الخرائط لا يعمل."

    if mode == "INBOUND":
        starts = list(range(num_drivers)) 
        ends = [meeting_idx] * num_drivers
    else:
        starts = [meeting_idx] * num_drivers
        ends = list(range(num_drivers))

    manager = pywrapcp.RoutingIndexManager(len(all_locations), num_drivers, starts, ends)
    routing = pywrapcp.RoutingModel(manager)
    
    # دالة التكلفة (نركز هنا على المسافة الواقعية)
    def time_callback(from_index, to_index):
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        
        base_time = time_matrix[from_node][to_node]
        traffic_time = base_time * TRAFFIC_MULTIPLIER
        
        service_time = 0
        if num_drivers <= to_node < meeting_idx:
             service_time = SERVICE_TIME_PER_STOP
             
        return int(traffic_time + service_time)

    transit_callback_index = routing.RegisterTransitCallback(time_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)
    
    # إجبار جميع السيارات على العمل لضمان التوزيع
    for i in range(num_drivers):
        routing.SetVehicleUsedWhenEmpty(True, i)

    # قيد بيت الفايز للسائقين أبو عمر وأبو عبدالله فقط
    abu_omar_idx = -1
    abu_abdullah_idx = -1
    for idx, drv in enumerate(active_drivers):
        if drv['id'] == 5: abu_omar_idx = idx
        if drv['id'] == 6: abu_abdullah_idx = idx

    fayez_node_idx = -1
    for idx, loc in enumerate(all_locations):
        if loc.get('id') == 9: fayez_node_idx = idx; break
    
    if fayez_node_idx != -1 and (abu_omar_idx != -1 or abu_abdullah_idx != -1):
        allowed = []
        if abu_omar_idx != -1: allowed.append(abu_omar_idx)
        if abu_abdullah_idx != -1: allowed.append(abu_abdullah_idx)
        routing.VehicleVar(manager.NodeToIndex(fayez_node_idx)).SetValues(allowed)

    # --- الأبعاد ---

    # 1. بُعد الوقت
    routing.AddDimension(transit_callback_index, 0, 100000, True, 'Time')
    time_dimension = routing.GetDimensionOrDie('Time')
    time_dimension.SetGlobalSpanCostCoefficient(0) 

    # 2. بُعد السعة المرنة
    def capacity_callback(from_index):
        node = manager.IndexToNode(from_index)
        return 1 if num_drivers <= node < meeting_idx else 0

    capacity_callback_index = routing.RegisterUnaryTransitCallback(capacity_callback)
    
    routing.AddDimension(
        capacity_callback_index,
        0,
        HARD_CAPACITY_LIMIT, 
        True, 
        'Capacity'
    )
    capacity_dimension = routing.GetDimensionOrDie('Capacity')

    for i in range(num_drivers):
        capacity_dimension.SetCumulVarSoftUpperBound(
            routing.End(i), 
            SOFT_CAPACITY_LIMIT, 
            CROWDING_PENALTY
        )

    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PARALLEL_CHEAPEST_INSERTION
    
    search_parameters.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    search_parameters.time_limit.seconds = 300 

    solution = routing.SolveWithParameters(search_parameters)
    
    results = {}
    if solution:
        for i in range(num_drivers):
            index = routing.Start(i)
            route_indices = []
            names = []
            while not routing.IsEnd(index):
                node = manager.IndexToNode(index)
                route_indices.append(node)
                names.append(all_locations[node]['name'])
                index = solution.Value(routing.NextVar(index))
            
            node = manager.IndexToNode(index)
            route_indices.append(node)
            names.append(all_locations[node]['name'])
            
            total_seconds = solution.Value(time_dimension.CumulVar(routing.End(i)))
            time_mins = math.ceil(total_seconds / 60)
            
            link = create_google_link(route_indices, all_locations)
            path_str = " ⬅️ ".join(names)
            pax_count = len(route_indices) - 2 
            
            extra_msg = ""
            if pax_count > SOFT_CAPACITY_LIMIT:
                extra_msg = f"\n⚠️ **(يوجد تزاحم: {pax_count} ركاب)**"

            results[active_drivers[i]['name']] = {
                "time": time_mins,
                "path": path_str,
                "link": link,
                "count": pax_count,
                "extra": extra_msg
            }
        return results
    return None

# --- 4. بوت التليجرام ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 أهلاً بك! أرسل رابط موقع التجمع أو الإحداثيات.", parse_mode='Markdown')
    return LOCATION

async def receive_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    coords = parse_coords(update.message.text)
    if not coords:
        await update.message.reply_text("❌ موقع غير صحيح.")
        return LOCATION
    context.user_data['meeting_point'] = coords
    reply_keyboard = [['الذهاب لنقطة التجمع', 'العودة للمنازل']]
    await update.message.reply_text(f"✅ الوجهة: {coords['lat']}, {coords['lng']}\nنوع الرحلة؟", 
                                    reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True))
    return TRIP_MODE

async def receive_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['mode'] = "INBOUND" if update.message.text == 'الذهاب لنقطة التجمع' else "OUTBOUND"
    reply_keyboard = [['نعم، الكل موجود', 'يوجد غياب']]
    await update.message.reply_text("هل الجميع موجود؟", 
                                    reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True))
    return ASK_ATTENDANCE

async def ask_attendance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['active_drivers'] = MASTER_DRIVERS[:]
    context.user_data['active_passengers'] = MASTER_PASSENGERS[:]
    if update.message.text == 'نعم، الكل موجود':
        await update.message.reply_text("🚀 جاري التوزيع (توزيع متوازي ذكي)...")
        return await run_solver(update, context)
    else:
        msg = "📋 **قائمة التحضير**\n\n**السائقون:**\n"
        for d in MASTER_DRIVERS: msg += f"{d['id']}. {d['name']}\n"
        msg += "\n**الركاب:**\n"
        for p in MASTER_PASSENGERS: msg += f"{p['id']}. {p['name']}\n"
        msg += "\n⚠️ أرسل أرقام الغائبين (مثال: `5, 12`)."
        await update.message.reply_text(msg, parse_mode='Markdown', reply_markup=ReplyKeyboardRemove())
        return GET_MISSING

async def receive_missing(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        missing_ids = [int(x.strip()) for x in update.message.text.split(',') if x.strip().isdigit()]
        context.user_data['active_drivers'] = [d for d in MASTER_DRIVERS if d['id'] not in missing_ids]
        context.user_data['active_passengers'] = [p for p in MASTER_PASSENGERS if p['id'] not in missing_ids]
        await update.message.reply_text(f"✅ تم التحديث. جاري الحساب...")
        return await run_solver(update, context)
    except:
        await update.message.reply_text("❌ خطأ في الأرقام.")
        return GET_MISSING

async def run_solver(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')
    results = solve_vrp(context.user_data['active_drivers'], context.user_data['active_passengers'], context.user_data['meeting_point'], context.user_data['mode'])
    
    if isinstance(results, str):
        await update.message.reply_text(f"❌ {results}")
    elif results:
        for driver_name, data in results.items():
            if data['count'] > 0:
                await update.message.reply_text(
                    f"🚘 *{driver_name}*{data.get('extra', '')}\n"
                    f"👥 الركاب: {data['count']}\n"
                    f"⏱️ الزمن المتوقع: `{data['time']} دقيقة`\n"
                    f"🗺️ المسار: {data['path']}\n"
                    f"🔗 [الخريطة]({data['link']})",
                    parse_mode='Markdown', disable_web_page_preview=True)
            else:
                await update.message.reply_text(
                    f"🚘 *{driver_name}*\n"
                    f"⚠️ (مسار مباشر)\n"
                    f"🔗 [الخريطة]({data['link']})",
                    parse_mode='Markdown', disable_web_page_preview=True)
        await update.message.reply_text("✅ تم الانتهاء. /start جديد.")
    else:
        await update.message.reply_text("❌ لم يتم العثور على حل.")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('🚫 تم الإلغاء.', reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

def main():
    application = Application.builder().token(TOKEN).build()
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            LOCATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_location)],
            TRIP_MODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_mode)],
            ASK_ATTENDANCE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_attendance)],
            GET_MISSING: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_missing)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    application.add_handler(conv_handler)
    print("Bot is running... (Parallel Insertion Logic)")
    application.run_polling()

if __name__ == "__main__":
    main()