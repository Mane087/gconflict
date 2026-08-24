Required Notice: Copyright 2026 <YOUR FULL LEGAL NAME OR COMPANY> (documentacion.lynxworxs@gmail.com)

---

## Summary (not part of the license)

English Reader is **source-available, not open source**. In plain terms:

| You want to... | Allowed? |
|---|---|
| Read, study and learn from the code | ✅ Yes |
| Run it for personal study, hobby or research | ✅ Yes |
| Fork it, modify it, share your changes | ✅ Yes, for noncommercial purposes |
| Use it at a school, university, NGO or public institution | ✅ Yes |
| Sell it, resell it, or bundle it into a paid product | ❌ Requires written permission |
| Use it internally at a for-profit company | ❌ Requires written permission |
| Offer it as a paid or ad-supported service | ❌ Requires written permission |

**Want a commercial license?** Contact documentacion.lynxworxs@gmail.com.
Commercial licenses are available and negotiable — just ask first.

The legally binding terms are below. Where this summary and the license text
disagree, the license text wins.

---

# PolyForm Noncommercial License 1.0.0

<https://polyformproject.org/licenses/noncommercial/1.0.0>

## Acceptance

In order to get any license under these terms, you must agree to them as both strict obligations and conditions to all your licenses.

## Copyright License

The licensor grants you a copyright license for the software to do everything you might do with the software that would otherwise infringe the licensor's copyright in it for any permitted purpose.  However, you may only distribute the software according to [Distribution License](#distribution-license) and make changes or new works based on the software according to [Changes and New Works License](#changes-and-new-works-license).

## Distribution License

The licensor grants you an additional copyright license to distribute copies of the software.  Your license to distribute covers distributing the software with changes and new works permitted by [Changes and New Works License](#changes-and-new-works-license).

## Notices

You must ensure that anyone who gets a copy of any part of the software from you also gets a copy of these terms or the URL for them above, as well as copies of any plain-text lines beginning with `Required Notice:` that the licensor provided with the software.  For example:

> Required Notice: Copyright Yoyodyne, Inc. (http://example.com)

## Changes and New Works License

The licensor grants you an additional copyright license to make changes and new works based on the software for any permitted purpose.

## Patent License

The licensor grants you a patent license for the software that covers patent claims the licensor can license, or becomes able to license, that you would infringe by using the software.

## Noncommercial Purposes

Any noncommercial purpose is a permitted purpose.

## Personal Uses

Personal use for research, experiment, and testing for the benefit of public knowledge, personal study, private entertainment, hobby projects, amateur pursuits, or religious observance, without any anticipated commercial application, is use for a permitted purpose.

## Noncommercial Organizations

Use by any charitable organization, educational institution, public research organization, public safety or health organization, environmental protection organization, or government institution is use for a permitted purpose regardless of the source of funding or obligations resulting from the funding.

## Fair Use

You may have "fair use" rights for the software under the law. These terms do not limit them.

## No Other Rights

These terms do not allow you to sublicense or transfer any of your licenses to anyone else, or prevent the licensor from granting licenses to anyone else.  These terms do not imply any other licenses.

## Patent Defense

If you make any written claim that the software infringes or contributes to infringement of any patent, your patent license for the software granted under these terms ends immediately. If your company makes such a claim, your patent license ends immediately for work on behalf of your company.

## Violations

The first time you are notified in writing that you have violated any of these terms, or done anything with the software not covered by your licenses, your licenses can nonetheless continue if you come into full compliance with these terms, and take practical steps to correct past violations, within 32 days of receiving notice.  Otherwise, all your licenses end immediately.

## No Liability

***As far as the law allows, the software comes as is, without any warranty or condition, and the licensor will not be liable to you for any damages arising out of these terms or the use or nature of the software, under any kind of legal claim.***

## Definitions

The **licensor** is the individual or entity offering these terms, and the **software** is the software the licensor makes available under these terms.

**You** refers to the individual or entity agreeing to these terms.

**Your company** is any legal entity, sole proprietorship, or other kind of organization that you work for, plus all organizations that have control over, are under the control of, or are under common control with that organization.  **Control** means ownership of substantially all the assets of an entity, or the power to direct its management and policies by vote, contract, or otherwise.  Control can be direct or indirect.

**Your licenses** are all the licenses granted to you for the software under these terms.

**Use** means anything you do with the software requiring one of your licenses.

---

## Scope (not part of the license)

The license above covers **only the original source code of this project**:

```
app.py
config.py
tts_service.py
recording_service.py
pronunciation_service.py
English Reader.spec
README.md
```

It does **not** cover the third-party dependencies listed in `requirements.txt`,
nor `espeak-ng`. Those are distributed by their own authors under their own
licenses, and some of them are copyleft:

| Component | License |
|---|---|
| phonemizer | GPL-3.0-or-later |
| espeak-ng (system binary) | GPL-3.0-or-later |
| edge-tts | LGPL-3.0 |
| customtkinter | CC0-1.0 |
| numpy | BSD-3-Clause (and others) |
| sounddevice | MIT |
| soundfile | BSD-3-Clause |
| pyobjc-* | MIT |

Because `phonemizer` and `espeak-ng` are GPL-3.0, **redistributing a combined
binary** (for example the PyInstaller `dist/English Reader.app` bundle) would
trigger GPL-3.0 copyleft on the combined work, and GPL-3.0 section 7 forbids
adding further restrictions such as the noncommercial condition above. Users
should therefore install the dependencies themselves from source, as documented
in the README. Do not publish prebuilt binaries without legal review.
