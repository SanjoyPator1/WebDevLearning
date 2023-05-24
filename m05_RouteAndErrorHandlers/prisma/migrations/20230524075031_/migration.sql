-- DropIndex
DROP INDEX "Product_id_belongsToId_key";

-- CreateIndex
CREATE INDEX "Product_id_belongsToId_idx" ON "Product"("id", "belongsToId");
