/** @odoo-module **/

import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { Component, useState, useRef, onMounted } from "@odoo/owl";

export class SignaturePadField extends Component {
    static template = "tazweed_esignature.SignaturePadField";
    static props = {
        ...standardFieldProps,
    };

    setup() {
        this.canvasRef = useRef("signatureCanvas");
        this.state = useState({
            isDrawing: false,
            signatureType: "draw",
            typedSignature: "",
            selectedFont: "dancing",
        });
        
        onMounted(() => {
            this.initCanvas();
        });
    }

    initCanvas() {
        const canvas = this.canvasRef.el;
        if (!canvas) return;
        
        this.ctx = canvas.getContext("2d");
        this.ctx.strokeStyle = "#000";
        this.ctx.lineWidth = 2;
        this.ctx.lineCap = "round";
        this.ctx.lineJoin = "round";
        
        canvas.addEventListener("mousedown", this.startDrawing.bind(this));
        canvas.addEventListener("mousemove", this.draw.bind(this));
        canvas.addEventListener("mouseup", this.stopDrawing.bind(this));
        canvas.addEventListener("mouseout", this.stopDrawing.bind(this));
        
        canvas.addEventListener("touchstart", this.handleTouchStart.bind(this));
        canvas.addEventListener("touchmove", this.handleTouchMove.bind(this));
        canvas.addEventListener("touchend", this.stopDrawing.bind(this));
    }

    startDrawing(e) {
        this.state.isDrawing = true;
        const rect = this.canvasRef.el.getBoundingClientRect();
        this.lastX = e.clientX - rect.left;
        this.lastY = e.clientY - rect.top;
    }

    draw(e) {
        if (!this.state.isDrawing) return;
        
        const rect = this.canvasRef.el.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        
        this.ctx.beginPath();
        this.ctx.moveTo(this.lastX, this.lastY);
        this.ctx.lineTo(x, y);
        this.ctx.stroke();
        
        this.lastX = x;
        this.lastY = y;
    }

    stopDrawing() {
        if (this.state.isDrawing) {
            this.state.isDrawing = false;
            this.saveSignature();
        }
    }

    handleTouchStart(e) {
        e.preventDefault();
        const touch = e.touches[0];
        const rect = this.canvasRef.el.getBoundingClientRect();
        this.state.isDrawing = true;
        this.lastX = touch.clientX - rect.left;
        this.lastY = touch.clientY - rect.top;
    }

    handleTouchMove(e) {
        e.preventDefault();
        if (!this.state.isDrawing) return;
        
        const touch = e.touches[0];
        const rect = this.canvasRef.el.getBoundingClientRect();
        const x = touch.clientX - rect.left;
        const y = touch.clientY - rect.top;
        
        this.ctx.beginPath();
        this.ctx.moveTo(this.lastX, this.lastY);
        this.ctx.lineTo(x, y);
        this.ctx.stroke();
        
        this.lastX = x;
        this.lastY = y;
    }

    clearSignature() {
        const canvas = this.canvasRef.el;
        this.ctx.clearRect(0, 0, canvas.width, canvas.height);
        this.props.record.update({ [this.props.name]: false });
    }

    saveSignature() {
        const canvas = this.canvasRef.el;
        const dataUrl = canvas.toDataURL("image/png");
        const base64Data = dataUrl.split(",")[1];
        this.props.record.update({ [this.props.name]: base64Data });
    }

    setSignatureType(type) {
        this.state.signatureType = type;
        if (type === "type") {
            this.updateTypedSignature();
        }
    }

    onTypedSignatureChange(ev) {
        this.state.typedSignature = ev.target.value;
        this.updateTypedSignature();
    }

    setFont(font) {
        this.state.selectedFont = font;
        this.updateTypedSignature();
    }

    updateTypedSignature() {
        if (!this.state.typedSignature) return;
        
        const canvas = this.canvasRef.el;
        this.ctx.clearRect(0, 0, canvas.width, canvas.height);
        
        const fonts = {
            dancing: "'Dancing Script', cursive",
            allura: "'Allura', cursive",
            pacifico: "'Pacifico', cursive",
            sacramento: "'Sacramento', cursive",
        };
        
        this.ctx.font = `48px ${fonts[this.state.selectedFont]}`;
        this.ctx.fillStyle = "#000";
        this.ctx.textAlign = "center";
        this.ctx.textBaseline = "middle";
        this.ctx.fillText(this.state.typedSignature, canvas.width / 2, canvas.height / 2);
        
        this.saveSignature();
    }
}

registry.category("fields").add("signature_pad", SignaturePadField);
