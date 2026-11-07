#include "diagnostics.h"
#include "play_flow.h"
#include <filesystem>
#include <fstream>
#include <iostream>
#include <cmath>
#include <stdexcept>
#include <unistd.h>
#include <sys/resource.h>
#include <sys/wait.h>
#include <csignal>
#include <sys/stat.h>
using namespace racer;
void require(bool b, const char *why) { if (!b) throw std::runtime_error(why); }
std::string read(const std::filesystem::path &p) { std::ifstream f(p); return {std::istreambuf_iterator<char>(f), {}}; }
int main(int argc, char **argv) {
  auto root = argc > 1 ? std::filesystem::path(argv[1]) : std::filesystem::temp_directory_path() / ("racer-diagnostics-" + std::to_string(getpid()));
  std::filesystem::create_directories(root);
  try {
    std::ofstream(root/"hash-fixture")<<"abc";
    require(Diagnostics::fileHash(root/"hash-fixture")=="ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad","known file SHA256");
    require(Diagnostics::fileHash(root/"hash-fixture",2)=="unavailable","hash byte cap");
    std::filesystem::create_symlink(root/"hash-fixture",root/"hash-link");
    require(Diagnostics::fileHash(root/"hash-link")=="unavailable","hash refuses symlink");
    require(::mkfifo((root/"hash-fifo").c_str(),0600)==0,"FIFO fixture");
    require(Diagnostics::fileHash(root/"hash-fifo")=="unavailable","hash refuses FIFO without waiting");
    {
      Diagnostics sink(root / "history");
      require(sink.enabled(), "recorder enabled");
      PlayFlow flow((root / "private-token-SECRET-profile.txt").string(), &sink);
      flow.garage(); flow.store.save(flow.profile);
      const auto good = read(flow.store.path());
      std::filesystem::permissions(root, std::filesystem::perms::owner_read | std::filesystem::perms::owner_exec);
      flow.profile.garage.draft.acceleration = 1.2; flow.profile.garage.apply();
      require(!flow.store.save(flow.profile), "real permission failure");
      require(read(flow.store.path()) == good, "last good bytes preserved");
      std::filesystem::permissions(root, std::filesystem::perms::owner_all);
      require(flow.store.save(flow.profile), "retry succeeds");
      flow.startTest(TestKind::Acceleration); flow.rearming = false;
      for (int i = 0; i < 6000 && flow.session.active(); ++i) flow.tick({});
      require(flow.session.result().valid, "genuine saved test result");
      flow.startTest(TestKind::Acceleration); flow.rearming = false;
      flow.focus = false; flow.suspend(); flow.action(Action::Accept);
      require(flow.paused, "unfocused resume rejected");
      flow.focus = true; flow.action(Action::Accept); flow.rearming = false;
      flow.session.timeout = .001;
      for (int i = 0; i < 365 && flow.session.active(); ++i) flow.tick({});
      require(flow.session.phase() == TestPhase::Invalid, "timeout invalidates");
      flow.startTest(TestKind::Handling); flow.rearming = false;
      for (int i = 0; i < 360; ++i) flow.tick({});
      flow.sim.car.z = 497.49; flow.sim.car.speed = 10;
      flow.tick({1,0,0}); require(!flow.session.result().valid, "boundary invalid");
      flow.startTest(TestKind::Handling); flow.rearming = false; flow.action(Action::Reset);
      require(flow.profile.records.size() == 1, "invalid attempts never record");
      // Diagnostic fields escape newlines/quotes and serialize non-finite numbers as null.
      sink.event("serialization_fixture", {{"symbol", "quote\" newline\n"}, {"number", std::nan("")}});
    }
    {
      Diagnostics sink(root / "history");
      PlayFlow restart((root / "private-token-SECRET-profile.txt").string(), &sink);
      require(restart.profile.records.size() == 1, "retained save survives new recorder lifecycle");
      std::ofstream(root / "malformed") << "SECRET raw contents";
      ProfileStore broken(root / "malformed", &sink); Profile p;
      require(!broken.load(p) && !broken.save(p), "malformed load and blocked save");
    }
    std::string all;
    for (const auto &f : std::filesystem::directory_iterator(root / "history"))
      if (f.path().extension() == ".jsonl") all += read(f.path());
    require(all.find("SECRET") == std::string::npos && all.find(root.string()) == std::string::npos, "no raw paths or profile contents");
    require(all.find("temporary_open") != std::string::npos && all.find("timeout") != std::string::npos && all.find("boundary") != std::string::npos, "failure outcomes retained");
    {
      Diagnostics quota(root / "quota", 4096);
      for (int i = 0; i < 100; ++i) { quota.event("bounded_fixture", {{"n", i}}); quota.flush(); }
    }
    bool stop = false;
    for (const auto &f : std::filesystem::directory_iterator(root / "quota"))
      if (f.path().extension() == ".jsonl") { require(f.file_size() <= 4096, "run bounded"); stop |= read(f.path()).find("recording_stopped") != std::string::npos; }
    require(stop, "quota explicit");
    std::ofstream(root / "not-a-directory") << "preserve";
    { Diagnostics failed(root / "not-a-directory" / "history");
      require(!failed.enabled(), "unwritable sink disabled");
      PlayFlow f((root / "still-playable").string(), &failed); f.startTest(TestKind::Acceleration); f.rearming = false;
      for (int i = 0; i < 6000 && f.session.active(); ++i) f.tick({});
      require(f.session.result().valid, "telemetry failure does not break play"); }
    for (int i = 0; i < 16; ++i) { Diagnostics bounded(root / "admission"); require(bounded.enabled(), "sixteen sessions admitted"); }
    { Diagnostics full(root / "admission"); require(!full.enabled(), "seventeenth session explicitly refused"); }
    // Only this child gets a file-size limit. It forces a real writer error
    // after a successful open, without filling the disk or affecting the host.
    pid_t child = fork();
    require(child >= 0, "fork write-failure fixture");
    if (child == 0) {
      std::signal(SIGXFSZ, SIG_IGN);
      rlimit limits; getrlimit(RLIMIT_FSIZE, &limits); limits.rlim_cur = 1024;
      if (setrlimit(RLIMIT_FSIZE, &limits)) _exit(2);
      bool okay = false;
      {
        Diagnostics failed(root / "write-failure");
        for (int i = 0; i < 30; ++i) { failed.event("write_fixture", {{"ordinal", i}}); failed.flush(); }
        PlayFlow f((root / "post-write-failure-profile").string(), &failed);
        f.startTest(TestKind::Acceleration); f.rearming = false;
        for (int i = 0; i < 6000 && f.session.active(); ++i) f.tick({});
        okay = !failed.enabled() && f.session.result().valid;
      }
      _exit(okay ? 0 : 3);
    }
    int status = 0; waitpid(child, &status, 0);
    require(WIFEXITED(status) && WEXITSTATUS(status) == 0, "writer failure preserves play");
    std::cout << "PASS: permission failure/retry, restart, timeout/boundary/reset, redaction, run/admission quotas and recorder open/write failures\n";
    if (argc == 1) std::filesystem::remove_all(root);
  } catch (const std::exception &e) {
    std::filesystem::permissions(root, std::filesystem::perms::owner_all);
    std::cerr << e.what() << '\n'; return 1;
  }
}
