class LiveMap {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.eventSource = null;
        this.svg = null;
        this.serverCountry = 'DE';
        this.tooltip = null;
        this.targetDots = new Map();
        this.animationQueue = [];
        this.isAnimating = false;
        this.init();
    }

    async init() {
        await this.loadSVG();
        this.createTooltip();
        this.addServerIndicator();
        await this.loadTargets();
        this.startLiveUpdates();
        this.processAnimationQueue();
    }

    createTooltip() {
        this.tooltip = document.createElement('div');
        this.tooltip.id = 'map-tooltip';
        this.tooltip.style.cssText = `
            position: fixed;
            background: #c0c0c0;
            color: #000;
            padding: 5px 8px;
            font-size: 11px;
            font-family: "MS Sans Serif", sans-serif;
            border: 2px solid #808080;
            border-top-color: #fff;
            border-left-color: #fff;
            border-right-color: #000;
            border-bottom-color: #000;
            pointer-events: none;
            display: none;
            z-index: 9999;
        `;
        document.body.appendChild(this.tooltip);
    }

    async loadSVG() {
        const response = await fetch('/static/world.svg');
        const svgText = await response.text();
        this.container.innerHTML = svgText;
        this.svg = this.container.querySelector('svg');
        
        const paths = this.svg.querySelectorAll('path[id]');
        paths.forEach(path => {
            path.style.fill = '#0a0a0a';
            path.style.stroke = '#404040';
            path.style.strokeWidth = '0.5';
        });
    }

    addServerIndicator() {
        const center = this.getCountryCenter(this.serverCountry);
        if (!center) return;

        const serverPath = this.svg.querySelector(`#${this.serverCountry}`);


        const indicator = document.createElementNS('http://www.w3.org/2000/svg', 'g');
        
        const outerPulse = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
        outerPulse.setAttribute('x', center.x - 8);
        outerPulse.setAttribute('y', center.y - 8);
        outerPulse.setAttribute('width', '16');
        outerPulse.setAttribute('height', '16');
        outerPulse.setAttribute('fill', 'none');
        outerPulse.setAttribute('stroke', '#c266fcff');
        outerPulse.setAttribute('stroke-width', '2');
        outerPulse.setAttribute('opacity', '0.6');
        
        const animateSize = document.createElementNS('http://www.w3.org/2000/svg', 'animate');
        animateSize.setAttribute('attributeName', 'width');
        animateSize.setAttribute('from', '16');
        animateSize.setAttribute('to', '32');
        animateSize.setAttribute('dur', '2s');
        animateSize.setAttribute('repeatCount', 'indefinite');
        outerPulse.appendChild(animateSize);
        
        const animateHeight = document.createElementNS('http://www.w3.org/2000/svg', 'animate');
        animateHeight.setAttribute('attributeName', 'height');
        animateHeight.setAttribute('from', '16');
        animateHeight.setAttribute('to', '32');
        animateHeight.setAttribute('dur', '2s');
        animateHeight.setAttribute('repeatCount', 'indefinite');
        outerPulse.appendChild(animateHeight);
        
        const animateX = document.createElementNS('http://www.w3.org/2000/svg', 'animate');
        animateX.setAttribute('attributeName', 'x');
        animateX.setAttribute('from', center.x - 8);
        animateX.setAttribute('to', center.x - 16);
        animateX.setAttribute('dur', '2s');
        animateX.setAttribute('repeatCount', 'indefinite');
        outerPulse.appendChild(animateX);
        
        const animateY = document.createElementNS('http://www.w3.org/2000/svg', 'animate');
        animateY.setAttribute('attributeName', 'y');
        animateY.setAttribute('from', center.y - 8);
        animateY.setAttribute('to', center.y - 16);
        animateY.setAttribute('dur', '2s');
        animateY.setAttribute('repeatCount', 'indefinite');
        outerPulse.appendChild(animateY);
        
        const animateOpacity = document.createElementNS('http://www.w3.org/2000/svg', 'animate');
        animateOpacity.setAttribute('attributeName', 'opacity');
        animateOpacity.setAttribute('from', '0.6');
        animateOpacity.setAttribute('to', '0');
        animateOpacity.setAttribute('dur', '2s');
        animateOpacity.setAttribute('repeatCount', 'indefinite');
        outerPulse.appendChild(animateOpacity);
        
        const dot = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
        dot.setAttribute('x', center.x - 4);
        dot.setAttribute('y', center.y - 4);
        dot.setAttribute('width', '8');
        dot.setAttribute('height', '8');
        dot.setAttribute('fill', '#7b68a8');
        dot.setAttribute('stroke', '#fff');
        dot.setAttribute('stroke-width', '2');
        
        const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        text.setAttribute('x', center.x);
        text.setAttribute('y', center.y + 25);
        text.setAttribute('text-anchor', 'middle');
        text.setAttribute('fill', '#7b68a8');
        text.setAttribute('font-family', '"MS Sans Serif", sans-serif');
        text.setAttribute('font-size', '10');
        text.setAttribute('font-weight', 'bold');
        text.textContent = 'H0NEYPOT';
        
        indicator.appendChild(outerPulse);
        indicator.appendChild(dot);
        indicator.appendChild(text);
        this.svg.appendChild(indicator);
    }

    async loadTargets() {
        const response = await fetch('/api/targets');
        const targets = await response.json();
        
        targets.forEach(target => {
            if (target.country) {
                this.addTargetDot(target.ip, target.country, target.online);
            }
        });
    }

    getCountryCenter(countryCode) {
        const path = this.svg.querySelector(`#${countryCode}`);
        if (!path) return null;
        
        const bbox = path.getBBox();
        return {
            x: bbox.x + bbox.width / 2,
            y: bbox.y + bbox.height / 2
        };
    }

    findNonOverlappingPosition(countryCode, preferredPos) {
        const minDistance = 8;
        const maxAttempts = 50;
        
        let pos = preferredPos || this.getCountryCenter(countryCode);
        if (!pos) return null;
        
        for (let attempt = 0; attempt < maxAttempts; attempt++) {
            let hasOverlap = false;
            
            for (const [ip, dotData] of this.targetDots) {
                const dx = pos.x - dotData.x;
                const dy = pos.y - dotData.y;
                const distance = Math.sqrt(dx * dx + dy * dy);
                
                if (distance < minDistance) {
                    hasOverlap = true;
                    pos = {
                        x: pos.x + (Math.random() - 0.5) * 20,
                        y: pos.y + (Math.random() - 0.5) * 20
                    };
                    break;
                }
            }
            
            if (!hasOverlap) {
                return pos;
            }
        }
        
        return pos;
    }

    addTargetDot(ip, country, online) {
        if (!country) return;
        
        if (this.targetDots.has(ip)) {
            this.updateTargetDot(ip, online);
            return;
        }
        
        const center = this.getCountryCenter(country);
        const pos = this.findNonOverlappingPosition(country, center);
        if (!pos) return;
        
        const dot = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
        dot.setAttribute('x', pos.x - 2);
        dot.setAttribute('y', pos.y - 2);
        dot.setAttribute('width', '4');
        dot.setAttribute('height', '4');
        dot.setAttribute('fill', online ? '#00ff00' : '#808080');
        dot.setAttribute('stroke', '#fff');
        dot.setAttribute('stroke-width', '0.5');
        
        this.svg.appendChild(dot);
        
        this.targetDots.set(ip, {
            element: dot,
            x: pos.x,
            y: pos.y,
            country: country,
            online: online
        });
    }

    updateTargetDot(ip, online) {
        const dotData = this.targetDots.get(ip);
        if (!dotData) return;
        
        dotData.online = online;
        dotData.element.setAttribute('fill', online ? '#00ff00' : '#808080');
    }

    removeTargetDot(ip) {
        const dotData = this.targetDots.get(ip);
        if (!dotData) return;
        
        dotData.element.remove();
        this.targetDots.delete(ip);
    }

    queueAnimation(animationFn) {
        this.animationQueue.push(animationFn);
    }

    processAnimationQueue() {
        setInterval(() => {
            if (!this.isAnimating && this.animationQueue.length > 0) {
                const animationFn = this.animationQueue.shift();
                this.isAnimating = true;
                animationFn().finally(() => {
                    this.isAnimating = false;
                });
            }
        }, 100);
    }

    createPixelExplosion(x, y, color) {
        const pixels = [];
        const numPixels = 8;
        
        for (let i = 0; i < numPixels; i++) {
            const angle = (Math.PI * 2 * i) / numPixels;
            const pixel = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
            pixel.setAttribute('x', x - 2);
            pixel.setAttribute('y', y - 2);
            pixel.setAttribute('width', '4');
            pixel.setAttribute('height', '4');
            pixel.setAttribute('fill', color);
            this.svg.appendChild(pixel);
            pixels.push({ element: pixel, angle, distance: 0 });
        }
        
        let frame = 0;
        const maxFrames = 12;
        const interval = setInterval(() => {
            frame++;
            pixels.forEach(pixel => {
                pixel.distance = frame * 3;
                const newX = x + Math.cos(pixel.angle) * pixel.distance - 2;
                const newY = y + Math.sin(pixel.angle) * pixel.distance - 2;
                pixel.element.setAttribute('x', newX);
                pixel.element.setAttribute('y', newY);
                pixel.element.setAttribute('opacity', 1 - frame / maxFrames);
            });
            
            if (frame >= maxFrames) {
                clearInterval(interval);
                pixels.forEach(pixel => pixel.element.remove());
            }
        }, 50);
    }

    animatePacket(fromCode, toCode, color, type) {
        return new Promise((resolve) => {
            const from = this.getCountryCenter(fromCode);
            const to = this.getCountryCenter(toCode);
            
            if (!from || !to) {
                resolve();
                return;
            }
            
            const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
            line.setAttribute('x1', from.x);
            line.setAttribute('y1', from.y);
            line.setAttribute('x2', to.x);
            line.setAttribute('y2', to.y);
            line.setAttribute('stroke', color);
            line.setAttribute('stroke-width', '1');
            line.setAttribute('opacity', '0.5');
            
            if (type === 'dashed') {
                line.setAttribute('stroke-dasharray', '4,4');
            } else if (type === 'dotted') {
                line.setAttribute('stroke-dasharray', '2,2');
            }
            
            this.svg.appendChild(line);
            
            const packet = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
            packet.setAttribute('width', '5');
            packet.setAttribute('height', '5');
            packet.setAttribute('fill', color);
            packet.setAttribute('stroke', '#fff');
            packet.setAttribute('stroke-width', '1');
            
            this.svg.appendChild(packet);
            
            const dx = to.x - from.x;
            const dy = to.y - from.y;
            const steps = 25;
            let step = 0;
            
            const interval = setInterval(() => {
                step++;
                const progress = step / steps;
                
                packet.setAttribute('x', from.x + dx * progress - 2.5);
                packet.setAttribute('y', from.y + dy * progress - 2.5);
                
                if (step >= steps) {
                    clearInterval(interval);
                    this.createPixelExplosion(to.x, to.y, color);
                    packet.remove();
                    line.remove();
                    resolve();
                }
            }, 40);
        });
    }

    animateFileTransfer(fromCode, toCode) {
        return new Promise((resolve) => {
            const from = this.getCountryCenter(fromCode);
            const to = this.getCountryCenter(toCode);
            
            if (!from || !to) {
                resolve();
                return;
            }
            
            const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
            line.setAttribute('x1', from.x);
            line.setAttribute('y1', from.y);
            line.setAttribute('x2', to.x);
            line.setAttribute('y2', to.y);
            line.setAttribute('stroke', '#7b68a8');
            line.setAttribute('stroke-width', '2');
            line.setAttribute('opacity', '0.6');
            
            this.svg.appendChild(line);
            
            const packets = [];
            for (let i = 0; i < 5; i++) {
                const packet = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
                packet.setAttribute('width', '4');
                packet.setAttribute('height', '4');
                packet.setAttribute('fill', '#7b68a8');
                packet.setAttribute('stroke', '#fff');
                packet.setAttribute('stroke-width', '1');
                this.svg.appendChild(packet);
                packets.push({ element: packet, offset: i * 0.15 });
            }
            
            const dx = to.x - from.x;
            const dy = to.y - from.y;
            const steps = 35;
            let step = 0;
            
            const interval = setInterval(() => {
                step++;
                
                packets.forEach(p => {
                    const progress = Math.min(1, (step / steps) - p.offset);
                    if (progress >= 0) {
                        p.element.setAttribute('x', from.x + dx * progress - 2);
                        p.element.setAttribute('y', from.y + dy * progress - 2);
                        p.element.setAttribute('opacity', progress);
                    }
                });
                
                if (step >= steps + 6) {
                    clearInterval(interval);
                    this.createPixelExplosion(to.x, to.y, '#7b68a8');
                    packets.forEach(p => p.element.remove());
                    line.remove();
                    resolve();
                }
            }, 40);
        });
    }

    showAlert(data) {
        const alert = document.createElement('div');
        alert.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: #c0c0c0;
            border: 2px solid #808080;
            border-top-color: #fff;
            border-left-color: #fff;
            border-right-color: #000;
            border-bottom-color: #000;
            padding: 0;
            font-family: "MS Sans Serif", sans-serif;
            font-size: 11px;
            min-width: 300px;
            z-index: 10000;
            transform: translateX(400px);
            transition: transform 0.3s;
        `;
        
        const titleBar = document.createElement('div');
        titleBar.style.cssText = `
            background: #7b68a8;
            color: #fff;
            padding: 3px 5px;
            font-weight: bold;
            display: flex;
            justify-content: space-between;
            align-items: center;
        `;
        titleBar.textContent = 'NEW FILE DETECTED';
        
        const content = document.createElement('div');
        content.style.cssText = `
            padding: 10px;
            color: #000;
            background: #c0c0c0;
        `;
        content.innerHTML = `
            <div style="margin-bottom: 5px;"><strong>IP:</strong> ${data.ip}</div>
            ${data.hash ? `<div style="font-family: 'Courier New', monospace; font-size: 10px; word-break: break-all;">${data.hash.substring(0, 32)}...</div>` : ''}
        `;
        
        alert.appendChild(titleBar);
        alert.appendChild(content);
        document.body.appendChild(alert);

        setTimeout(() => alert.style.transform = 'translateX(0)', 10);
        setTimeout(() => {
            alert.style.transform = 'translateX(400px)';
            setTimeout(() => alert.remove(), 300);
        }, 5000);
    }

    startLiveUpdates() {
        this.eventSource = new EventSource('/api/live_updates');
        
        this.eventSource.onmessage = (event) => {
            const data = JSON.parse(event.data);
            
            if (data.type === 'new_connection' && data.country && data.ip) {
                this.addTargetDot(data.ip, data.country, true);
                this.queueAnimation(() => 
                    this.animatePacket(this.serverCountry, data.country, '#00ff00', 'solid')
                );
            } else if (data.type === 'target_status_change' && data.ip && data.country) {
                if (this.targetDots.has(data.ip)) {
                    this.updateTargetDot(data.ip, data.online);
                } else {
                    this.addTargetDot(data.ip, data.country, data.online);
                }
            } else if (data.type === 'request' && data.country) {
                this.queueAnimation(() => 
                    this.animatePacket(this.serverCountry, data.country, '#7b68a8', 'solid')
                );
            } else if (data.type === 'response' && data.country) {
                this.queueAnimation(() => 
                    this.animatePacket(data.country, this.serverCountry, '#9988bb', 'solid')
                );
            } else if (data.type === 'ping_request' && data.country) {
                this.queueAnimation(() => 
                    this.animatePacket(this.serverCountry, data.country, '#c0c0c0', 'dashed')
                );
            } else if (data.type === 'ping_response' && data.country) {
                this.queueAnimation(() => 
                    this.animatePacket(data.country, this.serverCountry, '#808080', 'dashed')
                );
            } else if (data.type === 'new_file') {
                this.showAlert(data);
                if (data.country) {
                    this.queueAnimation(() => 
                        this.animateFileTransfer(data.country, this.serverCountry)
                    );
                }
            }
        };
    }

    destroy() {
        if (this.eventSource) {
            this.eventSource.close();
        }
        if (this.tooltip) {
            this.tooltip.remove();
        }
        this.targetDots.forEach(dotData => dotData.element.remove());
        this.targetDots.clear();
    }
}

document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('live-map')) {
        window.liveMap = new LiveMap('live-map');
    }
});