/**
 * SenseGlove Bridge - stdin/stdout JSON bridge for Python integration
 * 
 * Reads commands from stdin (one per line), calls SenseGlove HandLayer API,
 * writes JSON responses to stdout (one per line).
 * 
 * Protocol:
 *   INIT                          -> {"ok":true,"version":"...","sensecom":true/false}
 *   STATUS                        -> {"ok":true,"connected":true/false,"gloves":N,"type":"..."}
 *   FFB f0 f1 f2 f3 f4           -> {"ok":true}  (force feedback 5 fingers, 0.0-1.0)
 *   VIBRO location level          -> {"ok":true}  (vibration at EHapticLocation, 0.0-1.0)
 *   WAVEFORM amp dur freq loc     -> {"ok":true}  (custom waveform)
 *   SQUEEZE level                 -> {"ok":true}  (wrist squeeze, 0.0-1.0)
 *   STOP                          -> {"ok":true}  (stop all haptics)
 *   QUIT                          -> exits
 */

#include <iostream>
#include <sstream>
#include <string>
#include <vector>
#include <cstdio>

#include <SenseGlove/Connect/SGConnect.hpp>
#include <SenseGlove/Core/SenseCom.hpp>
#include <SenseGlove/Core/Library.hpp>
#include <SenseGlove/Core/HandLayer.hpp>
#include <SenseGlove/Core/HandPose.hpp>
#include <SenseGlove/Core/CustomWaveform.hpp>
#include <SenseGlove/Core/HapticGlove.hpp>
#include <SenseGlove/Core/Tracking.hpp>

using namespace SGCore;

// Escape a string for JSON output
static std::string jsonEscape(const std::string& s) {
    std::string out;
    out.reserve(s.size() + 10);
    for (char c : s) {
        switch (c) {
            case '"':  out += "\\\""; break;
            case '\\': out += "\\\\"; break;
            case '\n': out += "\\n"; break;
            case '\r': out += "\\r"; break;
            case '\t': out += "\\t"; break;
            default:   out += c; break;
        }
    }
    return out;
}

static void respond(const std::string& json) {
    std::cout << json << std::endl;
    std::cout.flush();
}

static void respondOk() {
    respond("{\"ok\":true}");
}

static void respondError(const std::string& msg) {
    respond("{\"ok\":false,\"error\":\"" + jsonEscape(msg) + "\"}");
}

static void handleInit() {
    std::string version = Library::Version();
    bool sensecom = SenseCom::ScanningActive();
    if (!sensecom) {
        SenseCom::StartupSenseCom();
        sensecom = SenseCom::ScanningActive();
    }
    respond("{\"ok\":true,\"version\":\"" + jsonEscape(version) + 
            "\",\"sensecom\":" + (sensecom ? "true" : "false") + "}");
}

static void handleStatus() {
    bool rightConnected = HandLayer::DeviceConnected(true);
    bool leftConnected = HandLayer::DeviceConnected(false);
    int32_t gloves = HandLayer::GlovesConnected();
    
    std::string typeStr = "none";
    if (rightConnected) {
        EDeviceType dt = HandLayer::GetDeviceType(true);
        typeStr = SGDevice::ToString(dt);
    }
    
    bool supportsWaveform = false;
    bool supportsWristSqueeze = false;
    if (rightConnected) {
        supportsWaveform = HandLayer::SupportsCustomWaveform(true, EHapticLocation::WholeHand);
        supportsWristSqueeze = HandLayer::SupportsWristSqueeze(true);
    }
    
    respond("{\"ok\":true,\"right_connected\":" + std::string(rightConnected ? "true" : "false") +
            ",\"left_connected\":" + std::string(leftConnected ? "true" : "false") +
            ",\"gloves\":" + std::to_string(gloves) +
            ",\"type\":\"" + jsonEscape(typeStr) + "\"" +
            ",\"supports_waveform\":" + std::string(supportsWaveform ? "true" : "false") +
            ",\"supports_wrist_squeeze\":" + std::string(supportsWristSqueeze ? "true" : "false") +
            "}");
}

static void handleFFB(std::istringstream& iss) {
    std::vector<float> levels(5, 0.0f);
    for (int i = 0; i < 5; i++) {
        if (!(iss >> levels[i])) {
            respondError("FFB requires 5 float values");
            return;
        }
        if (levels[i] < 0.0f) levels[i] = 0.0f;
        if (levels[i] > 1.0f) levels[i] = 1.0f;
    }
    
    if (!HandLayer::DeviceConnected(true)) {
        respondError("Right hand not connected");
        return;
    }
    
    bool result = HandLayer::QueueCommand_ForceFeedbackLevels(true, levels, true);
    if (result) respondOk();
    else respondError("Failed to send FFB command");
}

static void handleVibro(std::istringstream& iss) {
    int location;
    float level;
    if (!(iss >> location >> level)) {
        respondError("VIBRO requires location(int) level(float)");
        return;
    }
    if (level < 0.0f) level = 0.0f;
    if (level > 1.0f) level = 1.0f;
    
    if (!HandLayer::DeviceConnected(true)) {
        respondError("Right hand not connected");
        return;
    }
    
    EHapticLocation loc = static_cast<EHapticLocation>(location);
    bool result = HandLayer::QueueCommand_VibroLevel(true, loc, level, true);
    if (result) respondOk();
    else respondError("Failed to send vibro command");
}

static void handleWaveform(std::istringstream& iss) {
    float amplitude, duration, frequency;
    int location;
    if (!(iss >> amplitude >> duration >> frequency >> location)) {
        respondError("WAVEFORM requires amplitude duration frequency location");
        return;
    }
    if (amplitude < 0.0f) amplitude = 0.0f;
    if (amplitude > 1.0f) amplitude = 1.0f;
    
    if (!HandLayer::DeviceConnected(true)) {
        respondError("Right hand not connected");
        return;
    }
    
    EHapticLocation loc = static_cast<EHapticLocation>(location);
    CustomWaveform waveform(amplitude, duration, frequency);
    bool result = HandLayer::SendCustomWaveform(true, waveform, loc);
    if (result) respondOk();
    else respondError("Failed to send waveform");
}

static void handleSqueeze(std::istringstream& iss) {
    float level;
    if (!(iss >> level)) {
        respondError("SQUEEZE requires level(float)");
        return;
    }
    if (level < 0.0f) level = 0.0f;
    if (level > 1.0f) level = 1.0f;
    
    if (!HandLayer::DeviceConnected(true)) {
        respondError("Right hand not connected");
        return;
    }
    
    if (!HandLayer::SupportsWristSqueeze(true)) {
        respondError("Wrist squeeze not supported");
        return;
    }
    
    bool result = HandLayer::QueueCommand_WristSqueeze(true, level, true);
    if (result) respondOk();
    else respondError("Failed to send squeeze command");
}

static void handleStop() {
    HandLayer::StopAllHaptics(true);
    respondOk();
}

int main() {
    // Disable buffering on stdout for real-time communication
    std::setvbuf(stdout, nullptr, _IONBF, 0);
    
    // Signal ready
    respond("{\"ok\":true,\"ready\":true}");
    
    std::string line;
    while (std::getline(std::cin, line)) {
        if (line.empty()) continue;
        
        std::istringstream iss(line);
        std::string cmd;
        iss >> cmd;
        
        if (cmd == "INIT") {
            handleInit();
        } else if (cmd == "STATUS") {
            handleStatus();
        } else if (cmd == "FFB") {
            handleFFB(iss);
        } else if (cmd == "VIBRO") {
            handleVibro(iss);
        } else if (cmd == "WAVEFORM") {
            handleWaveform(iss);
        } else if (cmd == "SQUEEZE") {
            handleSqueeze(iss);
        } else if (cmd == "STOP") {
            handleStop();
        } else if (cmd == "QUIT") {
            respond("{\"ok\":true,\"quit\":true}");
            break;
        } else {
            respondError("Unknown command: " + cmd);
        }
    }
    
    // Clean up haptics before exit
    HandLayer::StopAllHaptics(true);
    return 0;
}
