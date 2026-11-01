// Browser checks use test-only serial doubles; screenshots contain no fake device data.
const {chromium}=require('playwright');
const {spawn}=require('node:child_process');
const fs=require('node:fs');
const assert=require('node:assert/strict');
(async()=>{
  fs.mkdirSync('build/ui',{recursive:true});
  const server=spawn('python3',['-m','tools.dashboard','--no-open','--port','8765'],{stdio:'ignore'});
  let browser;
  try{
    for(let i=0;i<50;i++){try{await fetch('http://127.0.0.1:8765');break}catch{await new Promise(r=>setTimeout(r,100))}}
    browser=await chromium.launch({headless:true,executablePath:process.env.CHROME_BIN||'/usr/bin/google-chrome',args:['--no-sandbox']});
    const page=await browser.newPage({viewport:{width:1440,height:1200}});
    const errors=[];page.on('pageerror',e=>errors.push(String(e)));
    await page.goto('http://127.0.0.1:8765');
    await page.waitForFunction(()=>document.querySelector('#corpus').textContent!=='Loading the included reports…');
    await page.screenshot({path:'build/ui/dashboard-desktop.png',fullPage:true});
    await page.setViewportSize({width:390,height:844});
    assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false,'Mobile horizontal overflow');
    await page.screenshot({path:'build/ui/dashboard-mobile.png',fullPage:true});
    assert.equal(await page.locator('#mode').textContent(),'—','No fake live readings while disconnected');
    const test=await browser.newPage({viewport:{width:1280,height:1000}});
    test.on('pageerror',e=>errors.push(String(e)));
    await test.addInitScript(()=>{
      window.__commands=[];
      let controller;
      const record={type:'stats',status:'streaming',mode:3,muted:true,gain:0.05,primary_rms:0.02,reference_rms:0.03,
        output_rms:0,max_dsp_us:350,dsp_p95_upper_us:352,rx_overflows:0,io_errors:0,speech_probability:0.8,
        neural_id:'TEST-ONLY',band_gains:[.8,.8,.8,.8,.8,.8,.8,.8]};
      const port={
        readable:new ReadableStream({start(c){controller=c}}),
        writable:new WritableStream({write(bytes){const command=new TextDecoder().decode(bytes);window.__commands.push(command);
          if(command.includes('stats'))controller.enqueue(new TextEncoder().encode(JSON.stringify(record)+'\n'));}}),
        async open(){},async close(){if(this.readable.locked||this.writable.locked)throw Error('Streams left locked');window.__closed=true}
      };
      Object.defineProperty(navigator,'serial',{value:{requestPort:async()=>port},configurable:true});
    });
    await test.goto('http://127.0.0.1:8765');
    await test.getByRole('button',{name:'Connect USB device'}).click();
    await test.waitForFunction(()=>document.querySelector('#mode').textContent==='Neural hybrid');
    await test.getByRole('button',{name:'1 · Calibrate, quiet 3 s'}).click();
    await test.getByRole('button',{name:'Adaptive DSP',exact:true}).click();
    await test.getByRole('button',{name:'Neural hybrid',exact:true}).click();
    await test.locator('#volume').evaluate(e=>{e.value='0.125';e.dispatchEvent(new Event('change'))});
    await test.waitForFunction(()=>window.__commands.includes('gain 0.125\n'));
    await test.getByRole('button',{name:'Disconnect and mute'}).click();
    await test.waitForFunction(()=>document.querySelector('#connect').textContent==='Connect USB device');
    await test.waitForFunction(()=>window.__closed===true);
    const commands=await test.evaluate(()=>window.__commands);
    for(const expected of ['calibrate\n','mode dsp\n','mode hybrid\n','mute on\n'])assert(commands.includes(expected));
    assert.deepEqual(errors,[]);
    fs.writeFileSync('build/ui/checks.json',JSON.stringify({mobileOverflow:false,disconnectedReadings:'empty',serialControls:'passed',errors},null,2));
    console.log('Dashboard desktop/mobile layout and USB control-contract checks passed.');
  }finally{if(browser)await browser.close();server.kill();}
})().catch(e=>{console.error(e);process.exit(1)});
