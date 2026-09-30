async (page) => {
  const consoleErrors = [];
  page.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push(message.text());
  });
  page.on("pageerror", (error) => consoleErrors.push(error.message));
  const fail = (message, evidence = {}) => {
    throw new Error(`${message}: ${JSON.stringify(evidence)}`);
  };
  const expect = (condition, message, evidence = {}) => {
    if (!condition) fail(message, evidence);
  };

  await page.route("**/avatar-controller.mjs*", (route) => route.fulfill({
    status: 200,
    contentType: "application/javascript",
    body: "",
  }));
  await page.route("**/weather-config.json", (route) => route.fulfill({
    status: 200,
    contentType: "application/json",
    body: "null",
  }));
  await page.addInitScript(() => {
    class FakeWebSocket {
      static instances = [];
      constructor(url) {
        this.url = url;
        this.sent = [];
        this.readyState = 0;
        FakeWebSocket.instances.push(this);
        setTimeout(() => {
          this.readyState = 1;
          this.onopen?.({});
        }, 0);
      }
      send(data) { this.sent.push(data); }
      close() {
        this.readyState = 3;
        this.onclose?.({});
      }
    }
    window.WebSocket = FakeWebSocket;
    window.__fakeWebSockets = FakeWebSocket.instances;
    window.__wsEmit = (payload, index = FakeWebSocket.instances.length - 1) => {
      const socket = FakeWebSocket.instances[index];
      const data = payload instanceof ArrayBuffer ? payload : JSON.stringify(payload);
      socket?.onmessage?.({ data });
    };
    window.__wsClose = (index = FakeWebSocket.instances.length - 1) => {
      FakeWebSocket.instances[index]?.close();
    };
    window.JarvisAvatar = {
      calls: [],
      setState(state) { this.calls.push(["state", state]); },
      startStream(options) {
        this.calls.push(["start", options.generation]);
        return Promise.resolve(true);
      },
      pushPCM(buffer, generation) {
        this.calls.push(["pcm", generation, buffer.byteLength]);
        return true;
      },
      endStream(generation) { this.calls.push(["end", generation]); return true; },
      interrupt(generation) { this.calls.push(["interrupt", generation]); return true; },
      setVisualization(active) { this.calls.push(["visualization", active]); },
    };
  });

  await page.goto("http://127.0.0.1:8765/hud/?v=browser-reliability1");
  await page.waitForFunction(() => document.getElementById("wsState")?.textContent === "online");

  const emit = (payload, index) => page.evaluate(
    ({ payload, index }) => window.__wsEmit(payload, index),
    { payload, index },
  );
  const stop = page.getByRole("button", { name: "■ STOP" });
  const sent = () => page.evaluate(
    () => window.__fakeWebSockets.at(-1).sent.map((message) => JSON.parse(message)),
  );

  for (const phase of ["thinking", "tool_use"]) {
    await emit({ type: "run_started", run_id: `run-${phase}` });
    await emit({ type: "agent_status", state: phase, tool: "research", preview: "bounded" });
    await stop.click();
    const messages = await sent();
    expect(messages.at(-1)?.type === "stop_run", `STOP failed during ${phase}`, { messages });
    expect(await page.locator("#stateLabel").textContent() === "STANDBY", `HUD did not reset after ${phase}`);
  }

  await emit({ type: "run_started", run_id: "run-speaking" });
  await emit({ type: "agent_status", state: "speaking" });
  await emit({ type: "agent_status", state: "speaking" });
  await page.evaluate(() => window.__wsEmit(new Uint8Array([1, 2, 3, 4]).buffer));
  await page.evaluate(() => window.__wsEmit(new Uint8Array([5, 6, 7, 8]).buffer));
  await stop.click();
  await page.evaluate(() => window.__wsEmit(new Uint8Array([9, 10, 11, 12]).buffer));
  const audio = await page.evaluate(() => ({
    starts: window.JarvisAvatar.calls.filter((call) => call[0] === "start"),
    pcm: window.JarvisAvatar.calls.filter((call) => call[0] === "pcm"),
    interrupts: window.JarvisAvatar.calls.filter((call) => call[0] === "interrupt"),
    dropped: Number(document.getElementById("dbgDropped").textContent),
  }));
  expect(audio.starts.length === 1, "duplicate speaking events started duplicate playback", audio);
  expect(audio.pcm.length === 2, "accepted audio count changed after STOP", audio);
  expect(audio.interrupts.length === 1, "speaking STOP did not interrupt playback", audio);
  expect(audio.dropped === 1, "late audio after STOP was not dropped", audio);

  await emit({ type: "run_started", run_id: "run-reconnect" });
  await emit({ type: "agent_status", state: "speaking" });
  await page.evaluate(() => window.__wsClose(0));
  await page.waitForFunction(() => window.__fakeWebSockets.length === 2);
  await page.waitForFunction(() => document.getElementById("wsState")?.textContent === "online");
  const reconnectState = await page.evaluate(() => ({
    sockets: window.__fakeWebSockets.length,
    state: document.getElementById("stateLabel").textContent,
    stopDisplay: getComputedStyle(document.getElementById("stopBtn")).display,
  }));
  expect(reconnectState.state === "STANDBY", "reconnect did not reset HUD state", reconnectState);
  expect(reconnectState.stopDisplay === "none", "reconnect left STOP visible", reconnectState);

  await emit({ type: "agent_status", state: "thinking" }, 0);
  expect(
    await page.locator("#stateLabel").textContent() === "STANDBY",
    "closed socket mutated the active HUD",
  );
  await page.evaluate(() => window.__wsClose(0));
  await page.waitForTimeout(3200);
  expect(
    await page.evaluate(() => window.__fakeWebSockets.length) === 2,
    "closed socket scheduled a duplicate reconnect",
  );

  await emit({ type: "agent_status", state: "thinking" }, 1);
  expect(
    await page.locator("#stateLabel").textContent() === "PROCESSING",
    "active reconnected socket stopped receiving events",
  );
  expect(consoleErrors.length === 0, "browser console reported errors", { consoleErrors });

  return {
    passed: true,
    phases: ["thinking", "tool_use", "speaking", "reconnect"],
    audio,
    socketCount: await page.evaluate(() => window.__fakeWebSockets.length),
    consoleErrors,
  };
}
